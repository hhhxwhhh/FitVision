from rest_framework import serializers
from .models import AIAnalysisSession, AIModelConfig, PostureDiagnosis
from exercises.serializers import ExerciseSerializer

class PostureDiagnosisSerializer(serializers.ModelSerializer):
    suggested_exercises_detail = ExerciseSerializer(source='suggested_exercises', many=True, read_only=True)

    class Meta:
        model = PostureDiagnosis
        fields = (
            'id', 'diagnosis_type', 'score', 'summary', 'detailed_report', 
            'snapshot', 'landmarks_data', 'suggested_exercises', 
            'suggested_exercises_detail', 'created_at'
        )
        read_only_fields = ('user', 'created_at')

class AIAnalysisSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisSession
        fields = '__all__'

class AIModelConfigSerializer(serializers.ModelSerializer):
    exercise_name = serializers.ReadOnlyField(source='exercise.name')
    
    class Meta:
        model = AIModelConfig
        fields = '__all__'
