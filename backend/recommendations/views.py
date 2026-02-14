from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import RecommendedExercise, UserInteraction, UserState
from .serializers import RecommendedExerciseSerializer, UserInteractionSerializer, UserStateSerializer
from .services import HybridRecommender

class RecommendationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendedExerciseSerializer

    def get_queryset(self):
        return RecommendedExercise.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def user_status(self, request):
        """获取用户当前推荐相关的状态"""
        state, _ = UserState.objects.get_or_create(user=request.user)
        serializer = UserStateSerializer(state)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def get_personalized(self, request):
        """获取个性化推荐入口，支持 scenario 参数"""
        scenario = request.query_params.get('scenario', 'default')
        recommendations = HybridRecommender.get_recommendations(request.user, scenario=scenario)
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """对推荐结果进行反馈 (like/dislike/ignore)"""
        rec = self.get_object()
        action_type = request.data.get('action') # like, skip
        
        # 记录交互
        UserInteraction.objects.create(
            user=request.user,
            exercise=rec.exercise,
            interaction_type=action_type,
            score=1.0 if action_type == 'like' else -0.5
        )
        
        rec.is_seen = True
        rec.save()
        return Response({'status': 'feedback recorded'})

class InteractionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInteractionSerializer

    def get_queryset(self):
        return UserInteraction.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
