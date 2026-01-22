from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AIAnalysisSession, AIModelConfig
from .serializers import AIAnalysisSessionSerializer, AIModelConfigSerializer

class AIAnalysisSessionViewSet(viewsets.ModelViewSet):
    queryset = AIAnalysisSession.objects.all()
    serializer_class = AIAnalysisSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(record__session__user=self.request.user)

class AIModelConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AIModelConfig.objects.filter(is_active=True)
    serializer_class = AIModelConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='by-exercise/(?P<exercise_id>[^/.]+)')
    def by_exercise(self, request, exercise_id=None):
        config = self.queryset.filter(exercise_id=exercise_id).first()
        if config:
            serializer = self.get_serializer(config)
            return Response(serializer.data)
        return Response({"error": "No config found for this exercise"}, status=status.HTTP_404_NOT_FOUND)
