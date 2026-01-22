from rest_framework import serializers
from .models import UserDailyStats, UserBodyMetric, ExerciseProgress

class UserDailyStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDailyStats
        fields = '__all__'

class UserBodyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBodyMetric
        fields = '__all__'

class ExerciseProgressSerializer(serializers.ModelSerializer):
    exercise_name = serializers.ReadOnlyField(source='exercise.name')
    
    class Meta:
        model = ExerciseProgress
        fields = '__all__'
