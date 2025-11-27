from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, TrainingLog

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password')
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('username', 'nickname', 'gender', 'age', 'height', 'weight', 'injury_history', 'fitness_level')

class TrainingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingLog
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'calories', 'accuracy_score')