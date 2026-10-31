from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from exercises.models import Exercise
from training.models import UserTrainingExerciseRecord, UserTrainingSession

from .models import (
    Challenge,
    PersonalRecord,
    UserAchievement,
    UserChallenge,
    UserProgress,
    XPEvent,
)
from .services import (
    challenge_states,
    challenge_window,
    claim_challenge,
    claim_daily_quest,
    daily_training_loads,
    ensure_daily_quests,
    join_challenge,
    level_from_xp,
    readiness_snapshot,
    refresh_daily_quests,
    weekly_goal_for,
    weekly_goal_metrics,
    weekly_leaderboard,
    xp_for_level,
)


class GrowthServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="athlete", password="StrongPass123")
        self.exercise = Exercise.objects.create(
            name="杠铃卧推",
            description="胸部力量动作",
            target_muscle="chest",
            instructions="保持肩胛骨收紧",
        )

    def _session(self, *, completed=True, minutes=30, score=4.0, day=None):
        end = day or timezone.now()
        start = end - timedelta(minutes=minutes)
        return UserTrainingSession.objects.create(
            user=self.user,
            start_time=start,
            end_time=end if completed else None,
            is_completed=completed,
            total_exercises=1,
            completed_exercises=1 if completed else 0,
            calories_burned=220,
            performance_score=score,
        )

    def test_level_curve_is_monotonic(self):
        self.assertEqual(xp_for_level(1), 0)
        self.assertEqual(xp_for_level(2), 100)
        self.assertEqual(xp_for_level(3), 250)
        self.assertEqual(level_from_xp(0), 1)
        self.assertEqual(level_from_xp(99), 1)
        self.assertEqual(level_from_xp(100), 2)
        self.assertEqual(level_from_xp(250), 3)

    def test_session_completion_awards_xp_once_and_refreshes_stats(self):
        session = self._session()

        progress = UserProgress.objects.get(user=self.user)
        self.assertGreater(progress.xp, 0)
        self.assertEqual(progress.total_sessions, 1)
        self.assertEqual(progress.current_streak, 1)
        self.assertEqual(XPEvent.objects.filter(user=self.user, source="session").count(), 1)

        stats = self.user.stats
        stats.refresh_from_db()
        self.assertEqual(stats.total_trainings, 1)
        self.assertEqual(stats.weekly_trainings, 1)
        self.assertEqual(stats.total_training_days, 1)

        session.save()
        self.assertEqual(
            XPEvent.objects.filter(user=self.user, source="session").count(), 1
        )

    def test_personal_records_are_captured_on_completion(self):
        session = self._session(completed=False)
        UserTrainingExerciseRecord.objects.create(
            session=session,
            exercise=self.exercise,
            sets_completed=3,
            reps_completed=[10, 8, 8],
            weights_used=[40, 40, 40],
            form_score=92,
        )
        session.end_time = timezone.now()
        session.is_completed = True
        session.save()

        records = {
            record.record_type: record.value
            for record in PersonalRecord.objects.filter(user=self.user)
        }
        self.assertEqual(records["max_weight"], 40)
        self.assertEqual(records["max_reps"], 10)
        self.assertEqual(records["max_volume"], 1040)
        self.assertEqual(records["best_form"], 92)

    def test_first_session_unlocks_achievement(self):
        self._session()
        self.assertTrue(
            UserAchievement.objects.filter(
                user=self.user, achievement__code="first_session"
            ).exists()
        )
        self.assertTrue(
            XPEvent.objects.filter(user=self.user, source="achievement").exists()
        )

    def test_daily_quests_are_stable_and_claimable(self):
        first = ensure_daily_quests(self.user)
        second = ensure_daily_quests(self.user)
        self.assertEqual([quest.id for quest in first], [quest.id for quest in second])
        self.assertEqual(len(first), 3)

        quest = first[0]
        quest.progress = quest.target
        quest.completed_at = timezone.now()
        quest.save(update_fields=["progress", "completed_at"])

        claimed, awarded = claim_daily_quest(self.user, quest.id)
        self.assertTrue(awarded)
        self.assertIsNotNone(claimed.claimed_at)
        self.assertTrue(
            XPEvent.objects.filter(user=self.user, source="quest", reference_id=quest.id).exists()
        )

        with self.assertRaises(ValueError):
            claim_daily_quest(self.user, quest.id)

    def test_refresh_daily_quests_tracks_training_data(self):
        session = self._session(completed=False)
        UserTrainingExerciseRecord.objects.create(
            session=session,
            exercise=self.exercise,
            sets_completed=3,
            reps_completed=[10, 10, 10],
            weights_used=[30, 30, 30],
            form_score=90,
        )
        session.end_time = timezone.now()
        session.is_completed = True
        session.save()

        quests = refresh_daily_quests(self.user)
        metrics = {quest.metric: quest.progress for quest in quests}
        self.assertTrue(all(value > 0 for value in metrics.values()))

    def test_weekly_goal_claim(self):
        goal = weekly_goal_for(self.user)
        goal.target_sessions = 1
        goal.target_minutes = 0
        goal.save()

        self._session(minutes=25)
        goal.refresh_from_db()
        metrics = weekly_goal_metrics(self.user, goal)
        self.assertEqual(metrics["completed_days"], 1)
        self.assertTrue(metrics["can_claim"])

        from .services import claim_weekly_goal

        claimed, awarded = claim_weekly_goal(self.user)
        self.assertTrue(claimed.reward_claimed)
        self.assertEqual(awarded, 80)

    def test_challenge_window_uses_week_or_month(self):
        weekly = Challenge(
            code="window-weekly",
            title="周挑战",
            description="测试",
            period="weekly",
            metric="sessions",
            target=1,
        )
        monthly = Challenge(
            code="window-monthly",
            title="月挑战",
            description="测试",
            period="monthly",
            metric="sessions",
            target=1,
        )
        day = date(2026, 10, 31)
        self.assertEqual(challenge_window(weekly, day), (date(2026, 10, 26), date(2026, 11, 2)))
        self.assertEqual(challenge_window(monthly, day), (date(2026, 10, 1), date(2026, 11, 1)))

    def test_join_and_claim_challenge_is_idempotent(self):
        challenge = Challenge.objects.get(code="weekly_sessions")
        for _ in range(3):
            self._session()

        _, entry, created = join_challenge(self.user, challenge.id)
        self.assertTrue(created)
        self.assertEqual(entry.challenge_id, challenge.id)

        states = {state["challenge"].id: state for state in challenge_states(self.user)}
        state = states[challenge.id]
        self.assertTrue(state["is_joined"])
        self.assertTrue(state["is_completed"])
        self.assertTrue(state["can_claim"])
        self.assertGreaterEqual(state["progress"], challenge.target)

        _, claimed, state, achievements, awarded = claim_challenge(
            self.user, challenge.id
        )
        self.assertTrue(awarded)
        self.assertIsNotNone(claimed.claimed_at)
        self.assertTrue(state["is_claimed"])
        self.assertFalse(state["can_claim"])
        self.assertEqual(
            XPEvent.objects.filter(
                user=self.user, source="challenge", reference_id=claimed.id
            ).count(),
            1,
        )
        self.assertIsInstance(achievements, list)

        with self.assertRaises(ValueError):
            claim_challenge(self.user, challenge.id)

    def test_challenge_requires_join_and_completion(self):
        challenge = Challenge.objects.get(code="weekly_sessions")
        with self.assertRaises(ValueError):
            claim_challenge(self.user, challenge.id)

        join_challenge(self.user, challenge.id)
        with self.assertRaises(ValueError):
            claim_challenge(self.user, challenge.id)

        self._session()
        _, entry, created = join_challenge(self.user, challenge.id)
        self.assertFalse(created)
        self.assertFalse(entry.is_claimed)

    def test_private_users_are_hidden_from_leaderboard(self):
        other = User.objects.create_user(username="hidden", password="StrongPass123")
        other_progress, _ = UserProgress.objects.get_or_create(user=other)
        other_progress.is_public = False
        other_progress.save(update_fields=["is_public"])

        self._session()
        UserTrainingSession.objects.create(
            user=other,
            start_time=timezone.now() - timedelta(minutes=40),
            end_time=timezone.now(),
            is_completed=True,
            calories_burned=200,
            performance_score=3.0,
        )

        data = weekly_leaderboard(self.user)
        self.assertEqual(data["total_participants"], 1)
        self.assertTrue(data["me"]["is_me"])

    def test_readiness_snapshot_shape(self):
        snapshot = readiness_snapshot(self.user)
        self.assertIn("score", snapshot)
        self.assertGreaterEqual(snapshot["score"], 20)
        self.assertLessEqual(snapshot["score"], 99)
        for key in ("acwr", "fitness", "fatigue", "tsb", "intensity", "volume_multiplier", "reasons"):
            self.assertIn(key, snapshot)

    def test_daily_training_loads_aggregates_by_local_day(self):
        today = timezone.localdate()
        self._session(minutes=30, score=4.0, day=timezone.now())
        self._session(minutes=20, score=3.0, day=timezone.now())
        yesterday = timezone.now() - timedelta(days=1)
        self._session(minutes=45, score=5.0, day=yesterday)

        loads = daily_training_loads(self.user)
        self.assertEqual(len(loads), 2)
        by_day = {item.day: item for item in loads}
        self.assertEqual(by_day[today].minutes, 50.0)
        self.assertGreater(by_day[today].load, 0.0)
        self.assertAlmostEqual(by_day[yesterday.date()].minutes, 45.0, places=3)

    def test_readiness_reacts_to_a_training_spike(self):
        """连续大负荷后，模型应该自动下调建议强度。"""
        now = timezone.now()
        for offset in range(8):
            self._session(
                minutes=90,
                score=5.0,
                day=now - timedelta(days=offset),
            )
        spiked = readiness_snapshot(self.user)
        self.assertGreater(spiked["acwr"], 1.0)
        self.assertIn(spiked["intensity"], {"light", "rest", "moderate"})


class GrowthApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_overview_endpoint(self):
        response = self.client.get("/api/growth/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("progress", response.data)
        self.assertIn("daily_quests", response.data)
        self.assertIn("weekly_goal", response.data)
        self.assertEqual(len(response.data["daily_quests"]), 3)

    def test_week_goal_update(self):
        response = self.client.put(
            "/api/growth/weekly-goal/",
            {"target_sessions": 4, "target_minutes": 180},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["target_sessions"], 4)
        self.assertEqual(response.data["target_minutes"], 180)

    def test_week_goal_validation(self):
        response = self.client.put(
            "/api/growth/weekly-goal/",
            {"target_sessions": 9},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_challenges_endpoint_and_join(self):
        response = self.client.get("/api/growth/challenges/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 5)

        challenge = Challenge.objects.get(code="weekly_sessions")
        joined = self.client.post(f"/api/growth/challenges/{challenge.id}/join/")
        self.assertIn(joined.status_code, (200, 201))
        self.assertTrue(joined.data["challenge"]["is_joined"])

        again = self.client.post(f"/api/growth/challenges/{challenge.id}/join/")
        self.assertEqual(again.status_code, 200)
        self.assertFalse(again.data["created"])

    def test_claim_challenge_api_after_completion(self):
        challenge = Challenge.objects.get(code="weekly_sessions")
        for _ in range(3):
            UserTrainingSession.objects.create(
                user=self.user,
                start_time=timezone.now() - timedelta(minutes=20),
                end_time=timezone.now(),
                is_completed=True,
                total_exercises=1,
                completed_exercises=1,
                calories_burned=120,
                performance_score=4.0,
            )
        self.client.post(f"/api/growth/challenges/{challenge.id}/join/")
        response = self.client.post(f"/api/growth/challenges/{challenge.id}/claim/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["awarded_xp"], challenge.xp_reward)
        self.assertTrue(response.data["challenge"]["is_claimed"])
        self.assertFalse(response.data["challenge"]["can_claim"])

    def test_claim_challenge_before_completion_returns_400(self):
        challenge = Challenge.objects.get(code="weekly_sessions")
        self.client.post(f"/api/growth/challenges/{challenge.id}/join/")
        response = self.client.post(f"/api/growth/challenges/{challenge.id}/claim/")
        self.assertEqual(response.status_code, 400)

    def test_overview_includes_challenge_summary(self):
        response = self.client.get("/api/growth/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("challenges", response.data)
        self.assertGreaterEqual(response.data["challenges"]["total"], 5)

    def test_achievement_list(self):
        response = self.client.get("/api/growth/achievements/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["total"], 10)
        self.assertEqual(len(response.data["results"]), response.data["total"])

    def test_settings_toggle(self):
        response = self.client.put(
            "/api/growth/settings/", {"is_public": False}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_public"])
