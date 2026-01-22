from rest_framework import serializers
from .models import TrainingPlan, TrainingPlanDay, TrainingPlanExercise, UserTrainingSession, UserTrainingExerciseRecord
from exercises.models import Exercise
from users.models import UserProfile

class TrainingPlanExerciseSerializer(serializers.ModelSerializer):
    """训练计划动作序列化器"""
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)
    
    class Meta:
        model = TrainingPlanExercise
        fields = '__all__'
        read_only_fields = ('order',)


class TrainingPlanDaySerializer(serializers.ModelSerializer):
    """训练计划日序列化器"""
    exercises = TrainingPlanExerciseSerializer(many=True, read_only=True)
    
    class Meta:
        model = TrainingPlanDay
        fields = '__all__'


class TrainingPlanSerializer(serializers.ModelSerializer):
    """训练计划序列化器"""
    days_count = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TrainingPlan
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'updated_at')
        
    def get_days_count(self, obj):
        return obj.days.count()


class TrainingPlanDetailSerializer(serializers.ModelSerializer):
    """训练计划详情序列化器"""
    days = TrainingPlanDaySerializer(many=True, read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TrainingPlan
        exclude = ('created_at', 'updated_at')


class UserTrainingExerciseRecordSerializer(serializers.ModelSerializer):
    """用户训练动作记录序列化器"""
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)
    
    class Meta:
        model = UserTrainingExerciseRecord
        fields = '__all__'
        read_only_fields = ('session', 'created_at')


class UserTrainingSessionSerializer(serializers.ModelSerializer):
    """用户训练会话序列化器"""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    exercise_records_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserTrainingSession
        fields = '__all__'
        read_only_fields = ('user', 'start_time', 'end_time')
        
    def get_exercise_records_count(self, obj):
        return obj.exercise_records.count()


class UserTrainingSessionDetailSerializer(serializers.ModelSerializer):
    """用户训练会话详情序列化器"""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    exercise_records = UserTrainingExerciseRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserTrainingSession
        fields = '__all__'
        read_only_fields = ('user', 'start_time', 'end_time')