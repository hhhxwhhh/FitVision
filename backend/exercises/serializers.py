from rest_framework import serializers
from .models import ExerciseCategory, Exercise, UserExerciseRecord
from users.models import UserProfile

def _user_records_for(exercise, user):
    """取用户在某个动作上的记录（best / last）。

    列表接口会把当前页所有动作的记录一次性预取出来，
    这里优先读预取结果，避免每个动作各打一次数据库。
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    prefetched = getattr(exercise, '_prefetched_objects_cache', None) or {}
    cached = prefetched.get('userexerciserecord_set')
    if cached is not None:
        return list(cached)
    return list(
        UserExerciseRecord.objects.filter(user=user, exercise=exercise).order_by('-created_at')
    )

class ExerciseCategorySerializer(serializers.ModelSerializer):
    """动作分类序列化器"""
    exercises_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExerciseCategory
        fields = '__all__'
        
    def get_exercises_count(self, obj):
        # 视图层用 Count 注解时直接取值，避免每个分类再查一次。
        annotated = getattr(obj, 'exercises_count', None)
        if annotated is not None:
            return annotated
        return obj.exercise_set.filter(is_active=True).count()


class ExerciseSerializer(serializers.ModelSerializer):
    """动作序列化器"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Exercise
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ExerciseDetailSerializer(serializers.ModelSerializer):
    """动作详情序列化器，包含用户进度和详细显示文本"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    equipment_display = serializers.CharField(source='get_equipment_display', read_only=True)
    target_muscle_display = serializers.CharField(source='get_target_muscle_display', read_only=True)
    user_best_score = serializers.SerializerMethodField()
    user_last_record = serializers.SerializerMethodField()
    unlocks = serializers.SerializerMethodField()
    prerequisite_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Exercise
        exclude = ('created_at', 'updated_at')

    def get_unlocks(self, obj):
        return [{"id": e.id, "name": e.name} for e in obj.unlocks.all()]

    def get_prerequisite_list(self, obj):
        return [{"id": e.id, "name": e.name} for e in obj.prerequisites.all()]

    def get_user_best_score(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        records = _user_records_for(obj, user)
        if not records:
            return None
        return max((record.accuracy_score for record in records), default=None)

    def get_user_last_record(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        records = _user_records_for(obj, user)
        if not records:
            return None

        # records 按创建时间倒序，第一条即最近一次。
        last_record = records[0]
        return {
            'accuracy_score': last_record.accuracy_score,
            'count': last_record.count,
            'duration': last_record.duration,
            'created_at': last_record.created_at
        }


class UserExerciseRecordSerializer(serializers.ModelSerializer):
    """用户动作记录序列化器"""
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserExerciseRecord
        fields = '__all__'
        read_only_fields = ('user', 'created_at',)


class ExerciseWithUserProgressSerializer(serializers.ModelSerializer):
    """包含用户进度的动作序列化器"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    equipment_display = serializers.CharField(source='get_equipment_display', read_only=True)
    target_muscle_display = serializers.CharField(source='get_target_muscle_display', read_only=True)
    user_best_score = serializers.SerializerMethodField()
    user_last_record = serializers.SerializerMethodField()
    prerequisite_list = serializers.SerializerMethodField()
    unlocks = serializers.SerializerMethodField()
    
    class Meta:
        model = Exercise
        fields = '__all__'
        
    def get_prerequisite_list(self, obj):
        return [{"id": e.id, "name": e.name} for e in obj.prerequisites.all()]

    def get_unlocks(self, obj):
        return [{"id": e.id, "name": e.name} for e in obj.unlocks.all()]

    def get_user_best_score(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        records = _user_records_for(obj, user)
        if not records:
            return None
        return max((record.accuracy_score for record in records), default=None)

    def get_user_last_record(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        records = _user_records_for(obj, user)
        if not records:
            return None

        last_record = records[0]
        return {
            'accuracy_score': last_record.accuracy_score,
            'count': last_record.count,
            'duration': last_record.duration,
            'created_at': last_record.created_at
        }
