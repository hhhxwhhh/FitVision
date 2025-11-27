from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated # 导入权限控制
from .models import UserProfile, TrainingLog
from .serializers import UserRegisterSerializer, UserProfileSerializer, TrainingLogSerializer

# --- 1. 认证模块 (允许任何人访问) ---

class RegisterView(APIView):
    permission_classes = [AllowAny] # 允许任何人

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny] # 允许任何人

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': '登录成功',
                'username': user.username,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        return Response({'error': '账号或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

# --- 2. 业务模块 (必须带 Token 才能访问) ---

# 个人档案接口：既能查(GET)，也能改(PUT)
class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated] # 必须登录
    serializer_class = UserProfileSerializer

    # 告诉 Django：我要操作的是"当前登录用户"的档案
    def get_object(self):
        return self.request.user.profile

# 训练记录接口：既能看列表(GET)，也能上传新记录(POST)
class TrainingLogView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated] # 必须登录
    serializer_class = TrainingLogSerializer

    # 查：只返回属于"我"的记录，按时间倒序排
    def get_queryset(self):
        return TrainingLog.objects.filter(user=self.request.user).order_by('-created_at')

    # 存：自动把记录挂到"我"的名下，并简单算个卡路里
    def perform_create(self, serializer):
        # 简单卡路里公式：体重(kg) * 0.05 * 次数 (这里仅作演示)
        weight = self.request.user.profile.weight
        count = serializer.validated_data.get('count', 0)
        cal = weight * 0.05 * count
        
        serializer.save(user=self.request.user, calories=cal)
