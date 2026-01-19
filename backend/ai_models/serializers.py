from rest_framework import serializers
from .models import AIAnalysisSession, AIModelConfig

class AIAnalysisSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisSession
        fields = '__all__'

class AIModelConfigSerializer(serializers.ModelSerializer):
    exercise_name = serializers.ReadOnlyField(source='exercise.name')
    
    class Meta:
        model = AIModelConfig
        fields = '__all__'
