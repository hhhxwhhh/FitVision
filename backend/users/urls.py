from django.urls import path
from .views import RegisterView, LoginView, ProfileView, TrainingLogView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('training/logs/', TrainingLogView.as_view(), name='training_logs'),
]