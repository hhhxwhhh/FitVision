from rest_framework import serializers
from .models import ExerciseCategory, Exercise, UserExerciseRecord
from users.models import UserProfile

class ExerciseCategorySerializer(serializers.ModelSerializer):
    """动作分类序列化器"""
    exercises_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExerciseCategory
        fields = '__all__'
        
    def get_exercises_count(self, obj):
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
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            best_record = UserExerciseRecord.objects.filter(
                user=request.user,
                exercise=obj
            ).order_by('-accuracy_score').first()
            return best_record.accuracy_score if best_record else None
        return None
        
    def get_user_last_record(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            last_record = UserExerciseRecord.objects.filter(
                user=request.user,
                exercise=obj
            ).order_by('-created_at').first()
            
            if last_record:
                return {
                    'accuracy_score': last_record.accuracy_score,
                    'count': last_record.count,
                    'duration': last_record.duration,
                    'created_at': last_record.created_at
                }
        return None


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
        if request and hasattr(request, 'user'):
            best_record = UserExerciseRecord.objects.filter(
                user=request.user,
                exercise=obj
            ).order_by('-accuracy_score').first()
            return best_record.accuracy_score if best_record else None
        return None
        
    def get_user_last_record(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            last_record = UserExerciseRecord.objects.filter(
                user=request.user,
                exercise=obj
            ).order_by('-created_at').first()
            
            if last_record:
                return {
                    'accuracy_score': last_record.accuracy_score,
                    'count': last_record.count,
                    'duration': last_record.duration,
                    'created_at': last_record.created_at
                }
        return None