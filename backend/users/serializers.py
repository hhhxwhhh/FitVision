from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, TrainingLog

# 1. 注册序列化器 (保持不变)
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

# 2. 用户档案序列化器 (新加的)
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        # 这里列出你想让前端看到或修改的字段
        fields = ('username', 'nickname', 'gender', 'age', 'height', 'weight', 'injury_history', 'fitness_level')

# 3. 训练记录序列化器 (新加的)
class TrainingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingLog
        fields = '__all__' # 所有字段都导出来
        # user 和 created_at 由后端自动生成，前端不需要传
        read_only_fields = ('user', 'created_at', 'calories', 'accuracy_score')