from rest_framework import serializers

from .models import (
    Achievement,
    Challenge,
    PersonalRecord,
    UserAchievement,
    UserDailyQuest,
    WeeklyGoal,
)


class AchievementSerializer(serializers.ModelSerializer):
    unlocked = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()
    progress_value = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = (
            "id",
            "code",
            "title",
            "description",
            "category",
            "metric",
            "threshold",
            "xp_reward",
            "icon",
            "sort_order",
            "unlocked",
            "unlocked_at",
            "progress_value",
            "progress_percent",
        )

    def _unlocked(self, obj):
        return self.context.get("unlocked", {}).get(obj.id)

    def get_unlocked(self, obj):
        return self._unlocked(obj) is not None

    def get_unlocked_at(self, obj):
        user_achievement = self._unlocked(obj)
        return user_achievement.unlocked_at if user_achievement else None

    def _progress(self, obj):
        return float(self.context.get("metrics", {}).get(obj.metric, 0) or 0)

    def get_progress_value(self, obj):
        user_achievement = self._unlocked(obj)
        if user_achievement:
            return user_achievement.progress_value
        return round(self._progress(obj), 1)

    def get_progress_percent(self, obj):
        if self._unlocked(obj):
            return 100.0
        threshold = float(obj.threshold or 0)
        if threshold <= 0:
            return 100.0
        return round(min(100.0, self._progress(obj) / threshold * 100), 1)


class DailyQuestSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)
    is_claimed = serializers.BooleanField(read_only=True)
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = UserDailyQuest
        fields = (
            "id",
            "date",
            "code",
            "title",
            "description",
            "metric",
            "target",
            "progress",
            "xp_reward",
            "is_completed",
            "is_claimed",
            "completed_at",
            "claimed_at",
            "progress_percent",
        )

    def get_progress_percent(self, obj):
        target = float(obj.target or 0)
        if target <= 0:
            return 100.0
        return round(min(100.0, float(obj.progress) / target * 100), 1)


class WeeklyGoalSerializer(serializers.ModelSerializer):
    completed_days = serializers.SerializerMethodField()
    completed_minutes = serializers.SerializerMethodField()
    days_percent = serializers.SerializerMethodField()
    minutes_percent = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyGoal
        fields = (
            "id",
            "week_start",
            "target_sessions",
            "target_minutes",
            "completed_days",
            "completed_minutes",
            "days_percent",
            "minutes_percent",
            "can_claim",
            "reward_claimed",
        )

    def _metrics(self):
        return self.context.get("metrics", {})

    def get_completed_days(self, obj):
        return self._metrics().get("completed_days", 0)

    def get_completed_minutes(self, obj):
        return self._metrics().get("completed_minutes", 0)

    def get_days_percent(self, obj):
        return self._metrics().get("days_percent", 0)

    def get_minutes_percent(self, obj):
        return self._metrics().get("minutes_percent", 0)

    def get_can_claim(self, obj):
        return self._metrics().get("can_claim", False)


class PersonalRecordSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)
    record_type_label = serializers.CharField(
        source="get_record_type_display", read_only=True
    )
    target_muscle = serializers.CharField(
        source="exercise.target_muscle", read_only=True
    )

    class Meta:
        model = PersonalRecord
        fields = (
            "id",
            "exercise",
            "exercise_name",
            "target_muscle",
            "record_type",
            "record_type_label",
            "value",
            "achieved_at",
            "session",
        )


class ChallengeSerializer(serializers.ModelSerializer):
    period_label = serializers.CharField(source="get_period_display", read_only=True)
    metric_label = serializers.CharField(source="get_metric_display", read_only=True)
    period_start = serializers.SerializerMethodField()
    period_end = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    is_claimed = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()
    joined_at = serializers.SerializerMethodField()
    claimed_at = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = (
            "id",
            "code",
            "title",
            "description",
            "period",
            "period_label",
            "metric",
            "metric_label",
            "target",
            "xp_reward",
            "icon",
            "sort_order",
            "period_start",
            "period_end",
            "progress",
            "progress_percent",
            "is_joined",
            "is_completed",
            "is_claimed",
            "can_claim",
            "joined_at",
            "claimed_at",
        )

    def _state(self, obj):
        return self.context.get("states", {}).get(obj.id, {})

    def get_period_start(self, obj):
        return self._state(obj).get("period_start")

    def get_period_end(self, obj):
        return self._state(obj).get("period_end")

    def get_progress(self, obj):
        return self._state(obj).get("progress", 0)

    def get_progress_percent(self, obj):
        return self._state(obj).get("progress_percent", 0)

    def get_is_joined(self, obj):
        return self._state(obj).get("is_joined", False)

    def get_is_completed(self, obj):
        return self._state(obj).get("is_completed", False)

    def get_is_claimed(self, obj):
        return self._state(obj).get("is_claimed", False)

    def get_can_claim(self, obj):
        return self._state(obj).get("can_claim", False)

    def get_joined_at(self, obj):
        return self._state(obj).get("joined_at")

    def get_claimed_at(self, obj):
        return self._state(obj).get("claimed_at")


class AchievementSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ("id", "code", "title", "description", "category", "icon", "xp_reward")


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSummarySerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ("id", "achievement", "progress_value", "unlocked_at")
