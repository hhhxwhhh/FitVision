from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import UserProfile, TrainingLog
from .serializers import UserRegisterSerializer, UserProfileSerializer, TrainingLogSerializer

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)
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
        return self.request.user.profile

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