from rest_framework import generics,status, pagination
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone

from .models import ExerciseCategory, Exercise, UserExerciseRecord
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

