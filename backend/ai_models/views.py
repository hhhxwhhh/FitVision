from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AIAnalysisSession, AIModelConfig, PostureDiagnosis
from .serializers import AIAnalysisSessionSerializer, AIModelConfigSerializer, PostureDiagnosisSerializer
from .vlm_service import ChinaVLMService
from exercises.models import Exercise
import logging
import asyncio
from adrf.views import APIView as AsyncAPIView

logger = logging.getLogger(__name__)

class PostureDiagnosisViewSet(viewsets.ModelViewSet):
    """姿态诊断视图集"""
    queryset = PostureDiagnosis.objects.all()
    serializer_class = PostureDiagnosisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class VLMAnalysisAPIView(AsyncAPIView):
    """
    视觉大模型分析 API
    支持 realtime (实时纠错) 和 diagnosis (专业诊断报告) 两种模式
    """
    permission_classes = [permissions.IsAuthenticated]

    async def post(self, request):
        image_base64 = request.data.get('image_base64')
        mode = request.data.get('mode', 'realtime') # 'realtime' or 'diagnosis'
        
        if not image_base64:
            return Response({'detail': '缺少 image_base64 字段'}, status=status.HTTP_400_BAD_REQUEST)

        service = ChinaVLMService()
        try:
            # 调用异步分析接口
            result = await service.async_analyze_pose(
                {
                    'image_base64': image_base64,
                    'exercise_type': request.data.get('exercise_type', 'general'),
                    'landmarks': request.data.get('landmarks', []),
                    'motion_metrics': request.data.get('motion_metrics', {}),
                },
                mode=mode
            )

            # 如果是诊断模式，自动关联数据库中的动作建议
            if mode == 'diagnosis':
                targets = result.get('recommended_target_muscles', [])
                if targets:
                    matching_exercises = list(Exercise.objects.filter(target_muscle__in=targets)[:3])
                    result['system_recommendations'] = [
                        {'id': ex.id, 'name': ex.name, 'muscle': ex.target_muscle} 
                        for ex in matching_exercises
                    ]

            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error(f"VLM Analysis Error: {str(exc)}", exc_info=True)
            return Response(
                {'detail': 'AI 分析服务暂时不可用', 'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
