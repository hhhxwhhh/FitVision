from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.ExerciseCategoryList.as_view(), name='exercise-categories'),
    path('', views.ExerciseList.as_view(), name='exercises'),
    path('<int:id>/', views.ExerciseDetail.as_view(), name='exercise-detail'),
    path('records/', views.UserExerciseRecords.as_view(), name='user-exercise-records'),
    path('records/<int:exercise_id>/', views.ExerciseRecordsByExercise.as_view(), name='exercise-records'),
    path('record-performance/', views.record_exercise_performance, name='record-exercise-performance'),
    path('progress/<int:exercise_id>/', views.user_exercise_progress, name='user-exercise-progress'),
]