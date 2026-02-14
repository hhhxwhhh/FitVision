from django.urls import path
from .views import (RegisterView, LoginView, ProfileView, TrainingLogView,
                   UserGoalListCreateView, UserGoalDetailView, UserStatsView,
                   user_dashboard, MeView)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', MeView.as_view(), name='me'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('training/logs/', TrainingLogView.as_view(), name='training_logs'),
    path('goals/', UserGoalListCreateView.as_view(), name='user_goals'),
    path('goals/<int:pk>/', UserGoalDetailView.as_view(), name='user_goal_detail'),
    path('stats/', UserStatsView.as_view(), name='user_stats'),
    path('dashboard/', user_dashboard, name='user_dashboard'),
]