from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from .models import TrainingPlan, TrainingPlanDay, TrainingPlanExercise, UserTrainingSession, UserTrainingExerciseRecord
from .serializers import (
    TrainingPlanSerializer,
    TrainingPlanDetailSerializer,
    TrainingPlanDaySerializer,
    UserTrainingSessionSerializer,
    UserTrainingSessionDetailSerializer,
    UserTrainingExerciseRecordSerializer
)
from exercises.models import Exercise
from users.models import UserProfile

class TrainingPlanListView(generics.ListAPIView):
    """获取所有公开的训练计划，支持过滤、搜索和排序"""
    queryset = TrainingPlan.objects.filter(is_active=True, is_public=True)
    serializer_class = TrainingPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['goal', 'difficulty', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'difficulty', 'duration_weeks', 'created_at']
    ordering = ['-created_at']


class TrainingPlanDetailView(generics.RetrieveAPIView):
    """获取训练计划详情"""
    queryset = TrainingPlan.objects.filter(is_active=True)
    serializer_class = TrainingPlanDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_training_session(request):
    """开始一个新的训练会话"""
    user = request.user
    plan_id = request.data.get('plan_id')
    plan_day_id = request.data.get('plan_day_id')
    
    try:
        plan = None
        plan_day = None
        
        if plan_id:
            plan = get_object_or_404(TrainingPlan, id=plan_id, is_active=True)
            
        if plan_day_id:
            plan_day = get_object_or_404(TrainingPlanDay, id=plan_day_id)
            
            # 如果提供了plan_day但没有提供plan，则从plan_day获取plan
            if not plan:
                plan = plan_day.plan
                
        # 创建训练会话
        session = UserTrainingSession.objects.create(
            user=user,
            plan=plan,
            plan_day=plan_day,
            start_time=timezone.now(),
            total_exercises=plan_day.exercises.count() if plan_day else 0
        )
        
        serializer = UserTrainingSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def complete_training_session(request, session_id):
    """完成训练会话"""
    user = request.user
    session = get_object_or_404(UserTrainingSession, id=session_id, user=user)
    
    if session.is_completed:
        return Response({'error': '训练会话已结束'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 更新会话信息
    session.end_time = timezone.now() if not request.data.get('end_time') else request.data.get('end_time')
    session.is_completed = True
    session.completed_exercises = request.data.get('completed_exercises', session.total_exercises)
    session.calories_burned = request.data.get('calories_burned', 0)
    session.performance_score = request.data.get('performance_score', 0)
    session.save()
    
    # 计算训练时长（秒）
    duration_seconds = 0
    if session.end_time and session.start_time:
        duration_seconds = (session.end_time - session.start_time).total_seconds()
    
    # 同步数据到TrainingLog
    try:
        from users.models import TrainingLog
        TrainingLog.objects.create(
            user=user,
            action_name=f"训练计划: {session.plan.name if session.plan else '自定义训练'}",
            count=session.completed_exercises,
            duration=duration_seconds,
            accuracy_score=session.performance_score,
            calories=session.calories_burned
        )
    except Exception as e:
        print(e)
    
    serializer = UserTrainingSessionSerializer(session)
    return Response(serializer.data, status=status.HTTP_200_OK)


class UserTrainingSessionListView(generics.ListAPIView):
    """获取用户的训练会话记录"""
    serializer_class = UserTrainingSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserTrainingSession.objects.filter(user=self.request.user).order_by('-start_time')


class UserTrainingSessionDetailView(generics.RetrieveAPIView):
    """获取用户训练会话详情"""
    serializer_class = UserTrainingSessionDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserTrainingSession.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_training_exercise(request):
    """记录用户训练中的动作完成情况"""
    user = request.user
    session_id = request.data.get('session_id')
    
    session = get_object_or_404(UserTrainingSession, id=session_id, user=user)
    
    if session.is_completed:
        return Response({'error': '训练会话已结束，无法添加记录'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建训练动作记录
    record_data = request.data.copy()
    record_data['session'] = session.id
    
    serializer = UserTrainingExerciseRecordSerializer(data=record_data)
    if serializer.is_valid():
        record = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_training_exercise_record(request, record_id):
    """删除训练动作记录"""
    user = request.user
    record = get_object_or_404(UserTrainingExerciseRecord, id=record_id, session__user=user)
    
    # 检查会话是否已完成
    if record.session.is_completed:
        return Response({'error': '训练会话已结束，无法删除记录'}, status=status.HTTP_400_BAD_REQUEST)
    
    record.delete()
    return Response({'message': '删除成功'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_training_stats(request):
    """获取用户训练统计数据"""
    user = request.user
    
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None
    
    # 统计用户的训练数据
    total_sessions = UserTrainingSession.objects.filter(user=user, is_completed=True).count()
    
    # 计算总训练时长
    sessions_with_duration = UserTrainingSession.objects.filter(
        user=user, 
        is_completed=True
    ).exclude(end_time=None).exclude(start_time=None)
    
    total_duration = 0
    for session in sessions_with_duration:
        total_duration += (session.end_time - session.start_time).total_seconds()
    
    total_calories = UserTrainingSession.objects.filter(user=user, is_completed=True).aggregate(
        Sum('calories_burned')
    )['calories_burned__sum'] or 0
    
    best_record = UserTrainingSession.objects.filter(user=user, is_completed=True).order_by('-performance_score').first()
    
    # 最近7天的训练次数
    week_ago = timezone.now() - timedelta(days=7)
    weekly_sessions = UserTrainingSession.objects.filter(
        user=user, 
        is_completed=True, 
        start_time__gte=week_ago
    ).count()
    
    stats = {
        'profile_info': {
            'nickname': profile.nickname if profile else '',
            'gender': profile.gender if profile else '',
            'age': profile.age if profile else 0,
            'height': profile.height if profile else 0,
            'weight': profile.weight if profile else 0,
            'fitness_level': profile.fitness_level if profile else '',
        } if profile else None,
        'total_sessions': total_sessions,
        'total_duration': int(total_duration),  # 转换为整数秒
        'total_duration_formatted': str(timedelta(seconds=int(total_duration))),  # 格式化时间
        'weekly_sessions': weekly_sessions,
        'total_calories': round(total_calories, 2),
        'best_performance_score': best_record.performance_score if best_record else 0,
        'favorite_plan': best_record.plan.name if best_record and best_record.plan else '',
    }
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_plan_days(request, plan_id):
    """获取指定训练计划的所有天数安排"""
    user = request.user
    plan = get_object_or_404(TrainingPlan, id=plan_id, is_active=True)
    
    # 如果计划不是公开的，检查是否是创建者
    if not plan.is_public and plan.created_by != user:
        return Response({'error': '无权访问此训练计划'}, status=status.HTTP_403_FORBIDDEN)
    
    days = TrainingPlanDay.objects.filter(plan=plan).order_by('day_number')
    serializer = TrainingPlanDaySerializer(days, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)