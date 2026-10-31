from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.overview, name="growth-overview"),
    path("achievements/", views.achievements_list, name="growth-achievements"),
    path("quests/", views.daily_quests, name="growth-daily-quests"),
    path("quests/<int:quest_id>/claim/", views.claim_quest, name="growth-claim-quest"),
    path("weekly-goal/", views.weekly_goal, name="growth-weekly-goal"),
    path(
        "weekly-goal/claim/",
        views.claim_weekly_goal_reward,
        name="growth-claim-weekly-goal",
    ),
    path("records/", views.personal_records, name="growth-personal-records"),
    path("challenges/", views.challenges_list, name="growth-challenges"),
    path(
        "challenges/<int:challenge_id>/join/",
        views.join_challenge_view,
        name="growth-join-challenge",
    ),
    path(
        "challenges/<int:challenge_id>/claim/",
        views.claim_challenge_reward,
        name="growth-claim-challenge",
    ),
    path("leaderboard/", views.leaderboard, name="growth-leaderboard"),
    path("settings/", views.growth_settings, name="growth-settings"),
]
