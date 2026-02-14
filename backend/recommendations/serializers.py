from rest_framework import serializers
from .models import UserInteraction, RecommendedExercise, UserState
from exercises.serializers import ExerciseSerializer

class RecommendedExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)
    
    class Meta:
        model = RecommendedExercise
        fields = ['id', 'exercise', 'algorithm', 'score', 'rank', 'reason', 'is_seen', 'created_at']

class UserInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInteraction
        fields = '__all__'

class UserStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserState
        fields = '__all__'
