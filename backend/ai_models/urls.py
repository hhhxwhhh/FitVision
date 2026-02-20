from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIAnalysisSessionViewSet, AIModelConfigViewSet, PostureDiagnosisViewSet, VLMAnalysisAPIView

router = DefaultRouter()
router.register(r'sessions', AIAnalysisSessionViewSet)
router.register(r'configs', AIModelConfigViewSet)
router.register(r'posture-diagnosis', PostureDiagnosisViewSet, basename='posture_diagnosis')

urlpatterns = [
    path('', include(router.urls)),
    path('vlm-analysis/', VLMAnalysisAPIView.as_view(), name='vlm-analysis'),
]
