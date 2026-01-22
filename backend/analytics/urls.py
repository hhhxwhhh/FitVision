from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserDailyStatsViewSet, UserBodyMetricViewSet, ExerciseProgressViewSet

router = DefaultRouter()
router.register(r'daily-stats', UserDailyStatsViewSet)
router.register(r'body-metrics', UserBodyMetricViewSet)
router.register(r'exercise-progress', ExerciseProgressViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
