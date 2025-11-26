from django.urls import path
from .views import RegisterView, LoginView, ProfileView, TrainingLogView

urlpatterns = [
    # 认证
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # 业务功能 (新加的)
    path('profile/', ProfileView.as_view(), name='profile'),           # 个人档案
    path('training/logs/', TrainingLogView.as_view(), name='training_logs'), # 训练记录
]