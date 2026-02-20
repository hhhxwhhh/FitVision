from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, TrainingLog, UserGoal, UserStats

class UserRegisterSerializer(serializers.ModelSerializer):
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'password', 'password_confirm')
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("两次输入的密码不一致")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'avatar', 'nickname', 'gender', 'age', 'height', 'weight', 
                  'injury_history', 'fitness_level', 'activity_level', 'target_weight',
                  'target_date', 'daily_calorie_intake', 'daily_calorie_burn', 'bmi', 'bmr')
        read_only_fields = ('bmi', 'bmr')

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        email = user_data.get('email')
        if email:
            instance.user.email = email
            instance.user.save()
        return super().update(instance, validated_data)

class TrainingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingLog
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'calories', 'accuracy_score')

class UserGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoal
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

class UserStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStats
        fields = '__all__'
        read_only_fields = ('user', 'last_updated')