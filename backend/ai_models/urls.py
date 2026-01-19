from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIAnalysisSessionViewSet, AIModelConfigViewSet

router = DefaultRouter()
router.register(r'sessions', AIAnalysisSessionViewSet)
router.register(r'configs', AIModelConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
