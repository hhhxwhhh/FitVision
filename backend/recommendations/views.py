from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from .models import RecommendedExercise, UserInteraction, UserState
from .serializers import (
    RecommendedExerciseSerializer,
    UserInteractionSerializer,
    UserStateSerializer,
)
from .services import HybridRecommender


def _parse_limit(value, default=6, min_value=1, max_value=20):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min(parsed, max_value), min_value)


def _parse_brief(value, default=True):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


VALID_FEEDBACK_ACTIONS = {"like", "skip"}


class RecommendationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecommendedExerciseSerializer

    def get_queryset(self):
        return RecommendedExercise.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def user_status(self, request):
        """获取用户当前推荐相关的状态"""
        cache_key = f"rec_user_status:{request.user.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        state, _ = UserState.objects.get_or_create(user=request.user)
        serializer = UserStateSerializer(state)
        cache.set(cache_key, serializer.data, timeout=120)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def get_personalized(self, request):
        """获取个性化推荐入口，支持 scenario 参数"""
        scenario = request.query_params.get("scenario", "default")
        limit = _parse_limit(request.query_params.get("limit", 6))
        brief = _parse_brief(request.query_params.get("brief"), default=True)

        recommendations = HybridRecommender.get_recommendations(
            request.user, scenario=scenario, limit=limit
        )
        serializer = self.get_serializer(
            recommendations,
            many=True,
            context={**self.get_serializer_context(), "brief": brief},
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        """对推荐结果进行反馈 (like/skip)"""
        rec = self.get_object()
        action_type = (request.data.get("action") or "").strip().lower()
        if action_type not in VALID_FEEDBACK_ACTIONS:
            return Response(
                {
                    "detail": "Invalid action, allowed values: like, skip",
                    "allowed_actions": sorted(VALID_FEEDBACK_ACTIONS),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 记录交互
        UserInteraction.objects.create(
            user=request.user,
            exercise=rec.exercise,
            interaction_type=action_type,
            score=1.0 if action_type == "like" else -0.5,
        )

        rec.is_seen = True
        rec.save()
        # 用户反馈后，清理短缓存，确保后续状态与推荐尽快反映变化
        cache.delete(f"rec_user_status:{request.user.id}")
        return Response({"status": "feedback recorded"})


class InteractionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserInteractionSerializer

    def get_queryset(self):
        return UserInteraction.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


from recommendations.models import UserState
from training.models import UserTrainingExerciseRecord


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_status_view(request):
    """获取用户当前状态与本周训练容量统计"""
    user = request.user

    # 1. 获取强化学习引擎需要的疲劳状态
    state, _ = UserState.objects.get_or_create(user=user)

    # 2. 计算本周各部位的真实训练容量
    one_week_ago = timezone.now() - timedelta(days=7)
    recent_records = UserTrainingExerciseRecord.objects.filter(
        session__user=user, created_at__gte=one_week_ago
    ).select_related("exercise")

    # 初始化三个核心部位的容量为 0
    raw_volume = {"chest": 0.0, "legs": 0.0, "abs": 0.0}

    # 假设每周的及格目标容量是 3000kg (你可以根据 UserProfile 里的基础调整这个值)
    TARGET_VOLUME = 3000.0

    for record in recent_records:
        muscle = record.exercise.target_muscle
        # 我们前端只展示这三个，所以只统计这三个
        if muscle not in raw_volume:
            continue

        # 清洗 JSON 里的脏数据
        w_list = [
            float(w)
            for w in record.weights_used
            if str(w).replace(".", "", 1).isdigit()
        ]
        r_list = [int(r) for r in record.reps_completed if str(r).isdigit()]

        # 严谨计算容量 = 重量 * 次数
        if w_list and len(w_list) == len(r_list):
            vol = sum(w * r for w, r in zip(w_list, r_list))
        elif r_list:
            # 如果是俯卧撑这种自重动作，没有填重量，按固定系数(例如 20kg)折算
            vol = sum(r_list) * 20.0
        else:
            vol = 0.0

        raw_volume[muscle] += vol

    # 3. 组装成前端 Vue 需要的精确格式
    volume_stats = [
        {
            "name": "胸部",
            "percentage": min(int((raw_volume["chest"] / TARGET_VOLUME) * 100), 100),
        },
        {
            "name": "腿部",
            "percentage": min(int((raw_volume["legs"] / TARGET_VOLUME) * 100), 100),
        },
        {
            "name": "核心",
            "percentage": min(int((raw_volume["abs"] / TARGET_VOLUME) * 100), 100),
        },
    ]

    return Response(
        {"fatigue_level": state.fatigue_level, "volume_stats": volume_stats}
    )
