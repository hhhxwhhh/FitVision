from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Achievement, PersonalRecord, UserAchievement, UserProgress
from .serializers import (
    AchievementSerializer,
    ChallengeSerializer,
    DailyQuestSerializer,
    PersonalRecordSerializer,
    UserAchievementSerializer,
    WeeklyGoalSerializer,
)
from .services import (
    build_metrics,
    challenge_states,
    claim_challenge,
    claim_daily_quest,
    claim_weekly_goal,
    evaluate_achievements,
    intensity_distribution,
    join_challenge,
    level_progress,
    load_curve_for,
    mesocycle_plan,
    muscle_recovery_snapshot,
    readiness_snapshot,
    refresh_daily_quests,
    strength_history,
    strength_prescription,
    weekly_goal_for,
    weekly_goal_metrics,
    weekly_leaderboard,
)


def _client_error(message: str) -> Response:
    return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)


def _progress_payload(progress: UserProgress) -> dict:
    payload = level_progress(progress.xp)
    payload.update(
        {
            "current_streak": progress.current_streak,
            "longest_streak": progress.longest_streak,
            "last_training_date": progress.last_training_date,
            "total_sessions": progress.total_sessions,
            "is_public": progress.is_public,
        }
    )
    return payload


def _challenge_context(states: list[dict]) -> dict:
    return {"states": {state["challenge"].id: state for state in states}}


def _challenge_payload(challenge, states: list[dict]) -> dict:
    return ChallengeSerializer(
        challenge, context=_challenge_context(states)
    ).data


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    """成长体系总览：等级、连续天数、每日任务、周目标、成就与个人纪录。"""
    user = request.user
    # 指标只算一次：既用于成就判定，也用于返回体。
    metrics = build_metrics(user)
    evaluate_achievements(user, metrics=metrics)

    progress, _ = UserProgress.objects.get_or_create(user=user)
    quests = refresh_daily_quests(user)
    goal = weekly_goal_for(user)
    goal_metrics = weekly_goal_metrics(user, goal)

    unlocked_map = {
        item.achievement_id: item
        for item in UserAchievement.objects.filter(user=user)
    }
    achievements = Achievement.objects.filter(is_active=True)
    achievement_context = {"unlocked": unlocked_map, "metrics": metrics}
    preview = AchievementSerializer(
        achievements.order_by("sort_order", "id")[:4],
        many=True,
        context=achievement_context,
    ).data
    records = (
        PersonalRecord.objects.filter(user=user)
        .select_related("exercise")
        .order_by("-achieved_at")[:5]
    )
    challenges = challenge_states(user)
    challenge_context = _challenge_context(challenges)

    return Response(
        {
            "progress": _progress_payload(progress),
            "readiness": readiness_snapshot(user),
            "weekly_goal": WeeklyGoalSerializer(
                goal, context={"metrics": goal_metrics}
            ).data,
            "daily_quests": DailyQuestSerializer(quests, many=True).data,
            "achievements": {
                "unlocked": len(unlocked_map),
                "total": achievements.count(),
                "preview": preview,
                "recent": UserAchievementSerializer(
                    UserAchievement.objects.filter(user=user)
                    .select_related("achievement")
                    .order_by("-unlocked_at")[:3],
                    many=True,
                ).data,
            },
            "personal_records": PersonalRecordSerializer(records, many=True).data,
            "challenges": {
                "total": len(challenges),
                "joined": sum(1 for item in challenges if item["is_joined"]),
                "completed": sum(1 for item in challenges if item["is_claimed"]),
                "claimable": sum(1 for item in challenges if item["can_claim"]),
                "preview": ChallengeSerializer(
                    [item["challenge"] for item in challenges[:3]],
                    many=True,
                    context=challenge_context,
                ).data,
            },
            "metrics": {
                key: round(float(value), 1) if isinstance(value, float) else value
                for key, value in metrics.items()
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def achievements_list(request):
    user = request.user
    metrics = build_metrics(user)
    evaluate_achievements(user, metrics=metrics)
    unlocked_map = {
        item.achievement_id: item
        for item in UserAchievement.objects.filter(user=user)
    }
    achievements = Achievement.objects.filter(is_active=True)
    serializer = AchievementSerializer(
        achievements,
        many=True,
        context={"unlocked": unlocked_map, "metrics": metrics},
    )
    return Response(
        {
            "unlocked": len(unlocked_map),
            "total": achievements.count(),
            "results": serializer.data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daily_quests(request):
    quests = refresh_daily_quests(request.user)
    return Response(DailyQuestSerializer(quests, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def claim_quest(request, quest_id):
    try:
        quest, awarded = claim_daily_quest(request.user, quest_id)
    except ValueError as exc:
        return _client_error(str(exc))
    return Response(
        {
            "quest": DailyQuestSerializer(quest).data,
            "awarded_xp": quest.xp_reward if awarded else 0,
        }
    )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def weekly_goal(request):
    goal = weekly_goal_for(request.user)

    if request.method == "PUT":
        try:
            target_sessions = int(request.data.get("target_sessions", goal.target_sessions))
            target_minutes = int(request.data.get("target_minutes", goal.target_minutes))
        except (TypeError, ValueError):
            return _client_error("目标值必须是整数")
        if not 1 <= target_sessions <= 7:
            return _client_error("目标训练天数需要在 1 到 7 之间")
        if not 0 <= target_minutes <= 3000:
            return _client_error("目标训练分钟需要在 0 到 3000 之间")
        goal.target_sessions = target_sessions
        goal.target_minutes = target_minutes
        goal.save(update_fields=["target_sessions", "target_minutes", "updated_at"])

    metrics = weekly_goal_metrics(request.user, goal)
    return Response(WeeklyGoalSerializer(goal, context={"metrics": metrics}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def claim_weekly_goal_reward(request):
    try:
        goal, awarded = claim_weekly_goal(request.user)
    except ValueError as exc:
        return _client_error(str(exc))
    metrics = weekly_goal_metrics(request.user, goal)
    return Response(
        {
            "weekly_goal": WeeklyGoalSerializer(
                goal, context={"metrics": metrics}
            ).data,
            "awarded_xp": awarded,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def personal_records(request):
    records = (
        PersonalRecord.objects.filter(user=request.user)
        .select_related("exercise")
        .order_by("-achieved_at")
    )
    record_type = request.query_params.get("type")
    if record_type:
        records = records.filter(record_type=record_type)
    return Response(PersonalRecordSerializer(records, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def challenges_list(request):
    """当前周期的全部挑战与用户进度。"""
    states = challenge_states(request.user)
    serializer = ChallengeSerializer(
        [state["challenge"] for state in states],
        many=True,
        context=_challenge_context(states),
    )
    return Response(
        {
            "results": serializer.data,
            "joined": sum(1 for state in states if state["is_joined"]),
            "completed": sum(1 for state in states if state["is_claimed"]),
            "claimable": sum(1 for state in states if state["can_claim"]),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_challenge_view(request, challenge_id):
    try:
        challenge, _, created = join_challenge(request.user, challenge_id)
    except ValueError as exc:
        return _client_error(str(exc))

    states = challenge_states(request.user)
    return Response(
        {
            "challenge": _challenge_payload(challenge, states),
            "created": created,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def claim_challenge_reward(request, challenge_id):
    try:
        challenge, _, state, achievements, awarded = claim_challenge(
            request.user, challenge_id
        )
    except ValueError as exc:
        return _client_error(str(exc))

    states = challenge_states(request.user)
    if state is not None:
        states = [
            state if item["challenge"].id == challenge.id else item
            for item in states
        ]
    return Response(
        {
            "challenge": _challenge_payload(challenge, states),
            "awarded_xp": challenge.xp_reward if awarded else 0,
            "achievements": UserAchievementSerializer(
                achievements, many=True
            ).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def leaderboard(request):
    try:
        limit = int(request.query_params.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))
    return Response(weekly_leaderboard(request.user, limit=limit))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def load_curve_view(request):
    """最近 N 天的训练负荷曲线（体能 / 疲劳 / TSB / ACWR）。

    查询参数：`days`（默认 90，上限 180）、`step`（默认 1，抽样步长）。
    """
    def positive_int(raw, default, low, high):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(low, min(high, value))

    days = positive_int(request.query_params.get("days"), 90, 7, 180)
    step = positive_int(request.query_params.get("step"), 1, 1, 7)
    return Response(
        {
            "days": days,
            "step": step,
            "points": load_curve_for(request.user, days=days, step=step),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def muscle_recovery_view(request):
    """今日分肌群恢复状态。

    返回每个肌群的恢复度、残余疲劳、距完全恢复的小时数、本周有效组数与
    容量状态，外加今日建议优先练的肌群（`focus`）与应当避开的肌群（`avoid`）。
    """
    return Response(muscle_recovery_snapshot(request.user).as_dict())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def strength_view(request):
    """力量曲线：每个动作的 e1RM 序列与下一次训练的建议重量。

    查询参数：`days`（默认 120，上限 365）、`exercise_id`（可选，只看一个动作）。
    """
    def positive_int(raw, default, low, high):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(low, min(high, value))

    days = positive_int(request.query_params.get("days"), 120, 7, 365)
    exercises = strength_history(request.user, days=days)

    exercise_id = request.query_params.get("exercise_id")
    prescription = None
    if exercise_id:
        try:
            target_id = int(exercise_id)
        except (TypeError, ValueError):
            target_id = 0
        if target_id:
            exercises = [item for item in exercises if item["exercise_id"] == target_id]
            prescription = strength_prescription(
                request.user,
                target_id,
                target_reps=positive_int(request.query_params.get("reps"), 6, 1, 20),
                target_rir=positive_int(request.query_params.get("rir"), 2, 0, 5),
            )

    return Response({"days": days, "exercises": exercises, "prescription": prescription})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mesocycle_view(request):
    """训练中周期计划：把恢复、准备度与力量三个引擎合成为一份周计划。

    查询参数：`weeks`（默认 4，上限 8）、`days_per_week`（默认 4，上限 5）。
    """
    def bounded_int(raw, default, low, high):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(low, min(high, value))

    weeks = bounded_int(request.query_params.get("weeks"), 4, 1, 8)
    days = bounded_int(request.query_params.get("days_per_week"), 4, 1, 5)
    return Response(mesocycle_plan(request.user, weeks=weeks, days_per_week=days))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def intensity_view(request):
    """训练强度分布（TRIMP）报告。

    查询参数：`days`（默认 28，上限 180）、`weeks`（默认 4，上限 12）。
    """
    def bounded_int(raw, default, low, high):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return default
        return max(low, min(high, value))

    days = bounded_int(request.query_params.get("days"), 28, 7, 180)
    weeks = bounded_int(request.query_params.get("weeks"), 4, 1, 12)
    payload = intensity_distribution(request.user, days=days, weeks=weeks)
    payload["days"] = days
    payload["weeks"] = weeks
    return Response(payload)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def growth_settings(request):
    progress, _ = UserProgress.objects.get_or_create(user=request.user)

    if request.method == "PUT":
        raw = request.data.get("is_public")
        if isinstance(raw, bool):
            is_public = raw
        elif isinstance(raw, str):
            is_public = raw.strip().lower() in {"1", "true", "yes", "on"}
        else:
            return _client_error("is_public 必须是布尔值")
        progress.is_public = is_public
        progress.save(update_fields=["is_public", "updated_at"])

    return Response({"is_public": progress.is_public})
