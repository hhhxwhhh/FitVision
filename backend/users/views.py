from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, TrainingLog, UserGoal, UserStats
from .serializers import (UserRegisterSerializer, UserProfileSerializer, 
                         TrainingLogSerializer, UserGoalSerializer, 
                         UserStatsSerializer)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '注册成功',
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

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

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

class TrainingLogView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TrainingLogSerializer

    def get_queryset(self):
        return TrainingLog.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        weight = self.request.user.profile.weight
        count = serializer.validated_data.get('count', 0)
        cal = weight * 0.05 * count
        
        serializer.save(user=self.request.user, calories=cal)

class UserGoalListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserGoalSerializer

    def get_queryset(self):
        return UserGoal.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserGoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserGoalSerializer

    def get_queryset(self):
        return UserGoal.objects.filter(user=self.request.user)

class UserStatsView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserStatsSerializer

    def get_object(self):
        stats, _ = UserStats.objects.get_or_create(user=self.request.user)
        return stats

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard(request):
    """
    获取用户仪表板数据
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    stats, _ = UserStats.objects.get_or_create(user=request.user)
    recent_logs = TrainingLog.objects.filter(user=request.user).order_by('-created_at')[:5]
    active_goals = UserGoal.objects.filter(user=request.user, is_active=True, achieved=False)
    
    dashboard_data = {
        'profile': UserProfileSerializer(profile).data,
        'stats': UserStatsSerializer(stats).data,
        'recent_logs': TrainingLogSerializer(recent_logs, many=True).data,
        'active_goals': UserGoalSerializer(active_goals, many=True).data,
    }
    
    return Response(dashboard_data)