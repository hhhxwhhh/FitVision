from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecommendationViewSet, InteractionViewSet

router = DefaultRouter()
router.register(r'list', RecommendationViewSet, basename='recommendations')
router.register(r'interactions', InteractionViewSet, basename='interactions')

urlpatterns = [
    path('', include(router.urls)),
]
