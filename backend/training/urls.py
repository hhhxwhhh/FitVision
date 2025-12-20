from django.urls import path
from . import views

urlpatterns = [
    # 训练计划相关路由
    path('plans/', views.TrainingPlanListView.as_view(), name='training-plans'),
    path('plans/<int:id>/', views.TrainingPlanDetailView.as_view(), name='training-plan-detail'),
    path('plans/<int:plan_id>/days/', views.get_plan_days, name='training-plan-days'),
    
    # 训练会话相关路由
    path('sessions/', views.UserTrainingSessionListView.as_view(), name='user-training-sessions'),
    path('sessions/<int:pk>/', views.UserTrainingSessionDetailView.as_view(), name='user-training-session-detail'),
    path('sessions/start/', views.start_training_session, name='start-training-session'),
    path('sessions/<int:session_id>/complete/', views.complete_training_session, name='complete-training-session'),
    
    # 训练动作记录相关路由
    path('exercise-records/', views.record_training_exercise, name='record-training-exercise'),
    path('exercise-records/<int:record_id>/', views.delete_training_exercise_record, name='delete-training-exercise-record'),
    
    # 用户统计数据路由
    path('stats/', views.user_training_stats, name='user-training-stats'),
]