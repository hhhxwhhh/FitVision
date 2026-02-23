from rest_framework import generics,status, pagination
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone

from .models import ExerciseCategory, Exercise, UserExerciseRecord, ExerciseGraph
from .serializers import (
    ExerciseCategorySerializer, 
    ExerciseSerializer, 
    ExerciseDetailSerializer,
    UserExerciseRecordSerializer,
    ExerciseWithUserProgressSerializer
)
from users.models import UserProfile

class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class ExerciseCategoryList(generics.ListAPIView):
    """获取所有运动类别"""
    queryset=ExerciseCategory.objects.filter(is_active=True)
    serializer_class=ExerciseCategorySerializer
    permission_classes = [IsAuthenticated]

class ExerciseList(generics.ListAPIView):
    """获取所有动作列表，支持过滤、搜索和排序"""
    queryset = Exercise.objects.filter(is_active=True).order_by('order', 'id')
    serializer_class = ExerciseWithUserProgressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'difficulty', 'target_muscle', 'equipment']
    search_fields = ['name', 'english_name', 'description']
    ordering_fields = ['name', 'difficulty', 'order', 'id', 'level']
    ordering = ['order', 'id']

    def get_serializer_context(self):
        context=super().get_serializer_context()
        context['request']=self.request
        return context
    
class ExerciseDetail(generics.RetrieveAPIView):
    """获取动作详情，包括用户进度"""
    queryset = Exercise.objects.filter(is_active=True)
    serializer_class = ExerciseDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

from recommendations.services import KnowledgeGraphEngine
from recommendations.gnn_models import KnowledgeGraphGNN
import torch

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exercise_graph_data(request):
    """获取动作知识图谱数据 (集成 GNN 结构分析与个人进度)"""
    exercises = list(Exercise.objects.all().prefetch_related('prerequisites', 'unlocks')) # 获取所有动作
    ex_id_to_idx = {ex.id: i for i, ex in enumerate(exercises)}
    num_nodes = len(exercises)
    
    # 获取用户已完成的动作
    mastered_ids = set(UserExerciseRecord.objects.filter(
        user=request.user, 
        accuracy_score__gte=80  # 假设 80 分以上为“掌握”
    ).values_list('exercise_id', flat=True))

    # 构造邻接矩阵用于 GNN 分析 (基于前置关系)
    adj = torch.eye(num_nodes)
    for ex in exercises:
        for pre in ex.prerequisites.all():
            if pre.id in ex_id_to_idx:
                adj[ex_id_to_idx[pre.id], ex_id_to_idx[ex.id]] = 1.0

    # 获取学习路径权重 (ExerciseGraph)
    graph_transitions = ExerciseGraph.objects.select_related('from_exercise', 'to_exercise')
    transition_map = {}
    for gt in graph_transitions:
        transition_map[(gt.from_exercise_id, gt.to_exercise_id)] = gt.probability

    model = KnowledgeGraphGNN(num_nodes=num_nodes, feature_dim=16)
    x_indices = torch.arange(num_nodes)
    with torch.no_grad():
        node_embeddings = model(x_indices, adj)
        structural_scores = torch.norm(node_embeddings, dim=1).numpy()
    
    nodes = []
    links = []
    
    category_colors = {
        'chest': '#ff4d4f', 'back': '#40a9ff', 'legs': '#73d13d',
        'shoulders': '#ffc53d', 'arms': '#ff7a45', 'abs': '#9254de', 
        'glutes': '#eb2f96', 'full_body': '#fa8c16'
    }
    
    # 状态提示色
    MASTERED_COLOR = '#b7eb8f' # 浅绿
    LOCKED_COLOR = '#efefef'    # 浅灰
    READY_COLOR = '#fffbe6'     # 浅黄 (可解锁)

    for i, ex in enumerate(exercises):
        # 确定节点状态
        is_mastered = ex.id in mastered_ids
        # 检查是否可以进行（前置是否全部掌握）
        all_pres_mastered = all(p.id in mastered_ids for p in ex.prerequisites.all())
        
        node_status = 'locked'
        if is_mastered:
            node_status = 'mastered'
        elif all_pres_mastered:
            node_status = 'ready'
            
        target_muscle = ex.target_muscle
        gnn_score = float(structural_scores[i])
        symbol_size = 30 + (gnn_score * 10) + (ex.level * 5)
        
        # 节点样式优化
        item_style = {
            'color': category_colors.get(target_muscle, '#bfbfbf'),
            'borderColor': '#fff',
            'borderWidth': 2 if gnn_score > 1.5 else 0
        }
        
        # 如果已掌握，给一个外发光或特殊标记
        if is_mastered:
            item_style['borderColor'] = '#52c41a'
            item_style['borderWidth'] = 4
            item_style['shadowBlur'] = 10
            item_style['shadowColor'] = '#52c41a'

        nodes.append({
            'name': ex.name,
            'id': str(ex.id),
            'category': ex.get_target_muscle_display(),
            'symbolSize': min(symbol_size, 80),
            'value': round(gnn_score, 2),
            'status': node_status,
            'is_mastered': is_mastered,
            'gnn_insight': f"结构重要性: {round(gnn_score, 2)}",
            'itemStyle': item_style,
            'level': ex.level
        })
        
        for pre in ex.prerequisites.all():
            weight = transition_map.get((pre.id, ex.id), 0.1)
            line_color = '#91d5ff'
            if pre.id in mastered_ids and ex.id in mastered_ids:
                line_color = '#52c41a' # 已通关路径
            elif pre.id in mastered_ids:
                line_color = '#faad14' # 正在攻略路径

            links.append({
                'source': str(pre.id),
                'target': str(ex.id),
                'relation_label': '前置基础',
                'label': {'show': True, 'formatter': '前置基础', 'fontSize': 10},
                'lineStyle': {
                    'width': 2 + (weight * 3), 
                    'curveness': 0.2, 
                    'color': line_color,
                    'type': 'solid' if pre.id in mastered_ids else 'dashed'
                }
            })
            
    return Response({
        'nodes': nodes,
        'links': links,
        'categories': [{'name': v} for v in ['胸部', '背部', '腿部', '肩部', '手臂', '腹部', '臀部', '全身']],
        'stats': {
            'total': num_nodes,
            'mastered': len(mastered_ids),
            'percent': round((len(mastered_ids) / num_nodes * 100), 1) if num_nodes > 0 else 0
        }
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_exercise_performance(request):
    """记录用户动作练习表现"""

    data=request.data.copy()
    data['user']=request.user.id

    serializer=UserExerciseRecordSerializer(data=data)
    if serializer.is_valid():
        record=serializer.save()
        """保存成功，返回记录数据 同步数据到trainlog模块"""
        try:
            from users.models import TrainingLog
            TrainingLog.objects.create(
                user=request.user,
                action_name=record.exercise.name,
                count=record.count,
                duration=record.duration,
                accuracy_score=record.accuracy_score,
                calories=record.calories_burned
            )
        except Exception as e:
            print(e)
        return Response(serializer.data,status=status.HTTP_201_CREATED)
    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

class UserExerciseRecords(generics.ListAPIView):
    """获取用户的动作练习记录"""
    serializer_class = UserExerciseRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserExerciseRecord.objects.filter(user=self.request.user).order_by('-created_at')
    
class ExerciseRecordsByExercise(generics.ListAPIView):
    """获取用户特定动作的练习记录"""
    serializer_class = UserExerciseRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        exercise_id=self.kwargs['exercise_id']
        return UserExerciseRecord.objects.filter(
            user=self.request.user,
            exercise__id=exercise_id
        ).order_by('-created_at')
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_exercise_progress(request, exercise_id):
    """获取用户特定动作的练习进度"""
    user = request.user   

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None

    # 统计用户的练习数据
    total_exercises = UserExerciseRecord.objects.filter(user=user).count()
    total_duration = UserExerciseRecord.objects.filter(user=user).aggregate(
        Sum('duration')
    )['duration__sum'] or 0

    total_calories = UserExerciseRecord.objects.filter(user=user).aggregate(
        Sum('calories_burned')
    )['calories_burned__sum'] or 0

    best_record = UserExerciseRecord.objects.filter(user=user).order_by('-accuracy_score').first()
    
    # 获取最近一次记录
    latest_record = UserExerciseRecord.objects.filter(
        user=user, 
        exercise__id=exercise_id
    ).order_by('-created_at').first()

    stats = {
        'profile_info': {
            'nickname': profile.nickname if profile else '',
            'gender': profile.gender if profile else '',
            'age': profile.age if profile else 0,
            'height': profile.height if profile else 0,
            'weight': profile.weight if profile else 0,
            'fitness_level': profile.fitness_level if profile else '',
        } if profile else None,
        'total_exercises': total_exercises,
        'total_duration': total_duration,
        'total_calories': round(total_calories, 2),
        'best_accuracy_score': best_record.accuracy_score if best_record else 0,
        'best_exercise': best_record.exercise.name if best_record else '',
        'latest_record': {
            'accuracy_score': latest_record.accuracy_score if latest_record else 0,
            'count': latest_record.count if latest_record else 0,
            'duration': latest_record.duration if latest_record else 0,
            'created_at': latest_record.created_at if latest_record else None
        } if latest_record else None,
    }
    return Response(stats, status=status.HTTP_200_OK)

