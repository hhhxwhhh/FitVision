from django.contrib import admin

from .models import (
    Achievement,
    Challenge,
    PersonalRecord,
    UserAchievement,
    UserChallenge,
    UserDailyQuest,
    UserProgress,
    WeeklyGoal,
    XPEvent,
)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "category", "metric", "threshold", "xp_reward", "is_active")
    list_filter = ("category", "metric", "is_active")
    search_fields = ("title", "code", "description")
    ordering = ("sort_order", "id")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "progress_value", "unlocked_at")
    list_filter = ("achievement__category",)
    search_fields = ("user__username", "achievement__title")
    autocomplete_fields = ("user", "achievement")


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "xp", "current_streak", "longest_streak", "is_public")
    list_filter = ("level", "is_public")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)


@admin.register(UserDailyQuest)
class UserDailyQuestAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "title", "progress", "target", "claimed_at")
    list_filter = ("date", "metric")
    search_fields = ("user__username", "title", "code")
    autocomplete_fields = ("user",)


@admin.register(WeeklyGoal)
class WeeklyGoalAdmin(admin.ModelAdmin):
    list_display = ("user", "week_start", "target_sessions", "target_minutes", "reward_claimed")
    list_filter = ("week_start", "reward_claimed")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)


@admin.register(PersonalRecord)
class PersonalRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "record_type", "value", "achieved_at")
    list_filter = ("record_type",)
    search_fields = ("user__username", "exercise__name")
    autocomplete_fields = ("user", "exercise", "session")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "period",
        "metric",
        "target",
        "xp_reward",
        "is_active",
        "sort_order",
    )
    list_filter = ("period", "metric", "is_active")
    search_fields = ("title", "code", "description")
    ordering = ("sort_order", "id")


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "challenge",
        "period_start",
        "joined_at",
        "completed_at",
        "claimed_at",
    )
    list_filter = ("challenge__period", "challenge__metric", "period_start")
    search_fields = ("user__username", "challenge__title")
    autocomplete_fields = ("user", "challenge")


@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "amount", "reference_id", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("user__username", "note")
    autocomplete_fields = ("user",)
