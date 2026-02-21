from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AIAnalysisSession, AIModelConfig, PostureDiagnosis
from .serializers import AIAnalysisSessionSerializer, AIModelConfigSerializer, PostureDiagnosisSerializer
from .vlm_service import ChinaVLMService
import logging
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


class VLMAnalysisAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image_base64 = request.data.get('image_base64')
        if not image_base64:
            return Response({'detail': '缺少 image_base64 字段'}, status=status.HTTP_400_BAD_REQUEST)

        # 使用单例模式获取服务（同步接口）
        service = ChinaVLMService()
        try:
            # 使用同步方法进行 AI 分析
            result = service.analyze_pose(
                {
                    'image_base64': image_base64,
                    'exercise_type': request.data.get('exercise_type', 'general'),
                    'landmarks': request.data.get('landmarks', []),
                    'motion_metrics': request.data.get('motion_metrics', {}),
                }
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            # 增加详细错误日志
            logger.error(f"VLM View Error: {str(exc)}", exc_info=True)
            
            return Response(
                {
                    'detail': '视觉模型分析失败，可能是模型处理中发生异常。',
                    'error_msg': str(exc)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
