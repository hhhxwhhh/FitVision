from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from exercises.models import Exercise
from training.models import UserTrainingExerciseRecord, UserTrainingSession

from .models import (
    Achievement,
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
    muscle_recovery_snapshot,
    muscle_works,
    readiness_snapshot,    refresh_daily_quests,
    strength_history,
    strength_prescription,
    update_personal_records,
    weekly_goal_for,
    weekly_goal_metrics,
    weekly_leaderboard,
    xp_for_level,
)


def _local_noon(day):
    """把本地日期变成当天中午的 aware datetime，避免时区/午夜造成的漂移。"""
    return timezone.make_aware(datetime.combine(day, time(12, 0)))


def _keep_within_one_local_day(start, end, minutes):
    """让一次会话落在同一个本地日内。

    会话按 `start_time__date` 聚合，如果测试恰好在午夜后运行，`now - 30min`
    会落在前一天，"今天练了多久"这类断言就会翻车。把窗口整体挪到当天开始之后，
    时长保持不变。
    """
    day_start = timezone.make_aware(datetime.combine(timezone.localdate(end), time.min))
    if start < day_start:
        start = day_start
        end = start + timedelta(minutes=minutes)
    return start, end


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
        start, end = _keep_within_one_local_day(start, end, minutes)
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
        yesterday = timezone.localdate() - timedelta(days=1)
        self._session(minutes=45, score=5.0, day=_local_noon(yesterday))

        loads = daily_training_loads(self.user)
        self.assertEqual(len(loads), 2)
        by_day = {item.day: item for item in loads}
        self.assertEqual(by_day[today].minutes, 50.0)
        self.assertGreater(by_day[today].load, 0.0)
        self.assertAlmostEqual(by_day[yesterday].minutes, 45.0, places=3)

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

    def _api_session(self, minutes=40, score=4.0, offset=0):
        end = timezone.now() - timedelta(days=offset)
        start, end = _keep_within_one_local_day(end - timedelta(minutes=minutes), end, minutes)
        return UserTrainingSession.objects.create(
            user=self.user,
            start_time=start,
            end_time=end,
            is_completed=True,
            total_exercises=1,
            completed_exercises=1,
            calories_burned=220,
            performance_score=score,
        )

    def _api_record(self, muscle, *, hours_ago=0, sets=4, reps=12, seconds=0, form_score=80.0):
        exercise, _ = Exercise.objects.get_or_create(
            name=f"动作-{muscle}",
            defaults={"description": "测试", "target_muscle": muscle, "difficulty": "beginner"},
        )
        session = UserTrainingSession.objects.create(
            user=self.user,
            start_time=timezone.now() - timedelta(hours=hours_ago),
            end_time=timezone.now() - timedelta(hours=hours_ago) + timedelta(minutes=30),
            is_completed=True,
            total_exercises=1,
            completed_exercises=1,
            performance_score=4.0,
        )
        return UserTrainingExerciseRecord.objects.create(
            session=session,
            exercise=exercise,
            sets_completed=sets,
            reps_completed=[reps] * sets,
            duration_seconds_actual=seconds,
            form_score=form_score,
        )

    def test_muscle_recovery_endpoint(self):
        self._api_record("legs", hours_ago=3, sets=5, reps=12)

        response = self.client.get('/api/growth/muscle-recovery/')
        self.assertEqual(response.status_code, 200)
        muscles = {item['muscle']: item for item in response.data['muscles']}
        self.assertIn('legs', muscles)
        self.assertIn('recovery', muscles['legs'])
        self.assertIn('focus', response.data)
        self.assertIn('avoid', response.data)

    def test_muscle_recovery_marks_a_fresh_leg_day_as_fatigued(self):
        for _ in range(3):
            self._api_record("legs", hours_ago=1, sets=5, reps=12)

        muscles = {
            item['muscle']: item for item in self.client.get('/api/growth/muscle-recovery/').data['muscles']
        }
        self.assertIn('legs', self.client.get('/api/growth/muscle-recovery/').data['avoid'])
        self.assertLess(muscles['legs']['recovery'], 100.0)

    def test_muscle_works_reads_reps_and_seconds(self):
        self._api_record("abs", hours_ago=2, sets=3, reps=15, seconds=60)
        works = muscle_works(self.user)
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0].reps, 45)
        self.assertEqual(works[0].seconds, 60.0)

    def test_muscle_recovery_snapshot_returns_the_engine_object(self):
        self._api_record("chest", hours_ago=5)
        snapshot = muscle_recovery_snapshot(self.user)
        self.assertTrue(hasattr(snapshot, 'multiplier_for'))
        self.assertLessEqual(snapshot.multiplier_for('chest'), 1.2)

    def _api_weighted_record(self, exercise, *, days_ago=0, weight=80.0, reps=5, sets=3, form_score=85.0):
        session = UserTrainingSession.objects.create(
            user=self.user,
            start_time=timezone.now() - timedelta(days=days_ago),
            end_time=timezone.now() - timedelta(days=days_ago) + timedelta(minutes=25),
            is_completed=True,
            total_exercises=1,
            completed_exercises=1,
            performance_score=4.0,
        )
        return UserTrainingExerciseRecord.objects.create(
            session=session,
            exercise=exercise,
            sets_completed=sets,
            reps_completed=[reps] * sets,
            weights_used=[weight] * sets,
            form_score=form_score,
        )

    def test_strength_endpoint_returns_the_e1rm_curve(self):
        exercise = Exercise.objects.create(
            name="杠铃卧推", description="胸部力量动作", target_muscle="chest"
        )
        self._api_weighted_record(exercise, days_ago=10, weight=70, reps=5)
        self._api_weighted_record(exercise, days_ago=2, weight=80, reps=5)

        response = self.client.get('/api/growth/strength/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['exercises']), 1)
        entry = response.data['exercises'][0]
        self.assertEqual(entry['exercise_id'], exercise.id)
        self.assertEqual(len(entry['points']), 2)
        self.assertGreater(entry['e1rm'], entry['points'][0]['e1rm'])

    def test_strength_endpoint_filters_by_exercise(self):
        bench = Exercise.objects.create(
            name="杠铃卧推", description="胸部力量动作", target_muscle="chest"
        )
        squat = Exercise.objects.create(
            name="杠铃深蹲", description="腿部力量动作", target_muscle="legs"
        )
        self._api_weighted_record(bench, weight=80)
        self._api_weighted_record(squat, weight=120)

        response = self.client.get(f'/api/growth/strength/?exercise_id={squat.id}')
        self.assertEqual(len(response.data['exercises']), 1)
        self.assertEqual(response.data['exercises'][0]['exercise_id'], squat.id)
        self.assertIsNotNone(response.data['prescription'])
        self.assertTrue(response.data['prescription']['available'])

    def test_strength_prescription_uses_double_progression(self):
        bench = Exercise.objects.create(
            name="杠铃卧推", description="胸部力量动作", target_muscle="chest"
        )
        self._api_weighted_record(bench, weight=80, reps=6, sets=1)

        response = self.client.get(f'/api/growth/strength/?exercise_id={bench.id}&reps=6')
        prescription = response.data['prescription']
        self.assertTrue(prescription['available'])
        self.assertGreater(prescription['weight'], 80)
        self.assertEqual(prescription['target_reps'], 6)

    def test_strength_endpoint_without_records(self):
        response = self.client.get('/api/growth/strength/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['exercises'], [])
        self.assertIsNone(response.data['prescription'])

    def test_strength_endpoint_clamps_its_query_params(self):
        response = self.client.get('/api/growth/strength/?days=9999&reps=abc')
        self.assertEqual(response.data['days'], 365)

    def test_mesocycle_endpoint_returns_a_multi_week_plan(self):
        response = self.client.get('/api/growth/mesocycle/?weeks=4&days_per_week=3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_weeks'], 4)
        self.assertEqual(response.data['days_per_week'], 3)
        self.assertIn('weeks', response.data)
        self.assertIn('readiness', response.data)
        week = response.data['weeks'][0]
        self.assertIn('phase', week)
        self.assertIn('sessions', week)

    def test_mesocycle_clamps_its_query_params(self):
        response = self.client.get('/api/growth/mesocycle/?weeks=99&days_per_week=99')
        self.assertEqual(response.data['total_weeks'], 8)
        self.assertLessEqual(response.data['days_per_week'], 5)

    def test_mesocycle_uses_e1rm_to_prescribe_load(self):
        bench = Exercise.objects.create(
            name="杠铃卧推", description="胸部力量动作", target_muscle="chest"
        )
        # 记录放在几天前，让胸部回到"可用"状态（当天练过的肌群会被降权）。
        self._api_weighted_record(bench, days_ago=4, weight=80, reps=5, sets=3)

        response = self.client.get('/api/growth/mesocycle/?weeks=3&days_per_week=2')
        slots = [
            slot
            for week in response.data['weeks']
            for session in week['sessions']
            for slot in session['slots']
        ]
        self.assertTrue(slots)
        self.assertTrue(any(slot['based_on_e1rm'] for slot in slots))
        self.assertTrue(any(slot['weight'] > 0 for slot in slots))

    def test_mesocycle_without_data_still_returns_a_shape(self):
        response = self.client.get('/api/growth/mesocycle/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['weeks']), 4)
        self.assertIn('muscle_recovery', response.data)

    def test_mesocycle_autoregulation_tracks_the_readiness_score(self):
        from utils.periodization import autoregulation_factor

        response = self.client.get('/api/growth/mesocycle/')
        expected = autoregulation_factor(response.data['readiness'])
        self.assertAlmostEqual(response.data['autoregulation'], expected, places=3)
        self.assertLessEqual(response.data['autoregulation'], 1.0)
        self.assertGreaterEqual(response.data['autoregulation'], 0.6)

    def test_mesocycle_service_is_callable_directly(self):
        from .services import mesocycle_plan

        payload = mesocycle_plan(self.user, weeks=2, days_per_week=2)
        self.assertEqual(payload['total_weeks'], 2)
        self.assertIn('muscle_recovery', payload)

    def test_mesocycle_resolves_concrete_exercises(self):
        # 动作库里要有对应肌群的动作，周期化计划才能落到具体动作上。
        Exercise.objects.create(
            name="上斜哑铃卧推", description="胸部动作", target_muscle="chest", instructions="收肩胛"
        )
        Exercise.objects.create(
            name="平板支撑", description="核心动作", target_muscle="abs", instructions="塌腰"
        )
        self._api_record("chest", hours_ago=40, sets=2, reps=10)

        response = self.client.get('/api/growth/mesocycle/?weeks=2&days_per_week=2')
        slots = [
            slot
            for week in response.data['weeks']
            for session in week['sessions']
            for slot in session['slots']
        ]
        self.assertTrue(slots)
        exercises = [item for slot in slots for item in slot['exercises']]
        self.assertTrue(exercises)
        self.assertIn('exercise_id', exercises[0])
        self.assertIn('name', exercises[0])

    def test_mesocycle_exercises_carry_their_own_sets(self):
        Exercise.objects.create(
            name="平板支撑", description="核心动作", target_muscle="abs", instructions="塌腰"
        )
        self._api_record("chest", hours_ago=40, sets=2, reps=10)

        response = self.client.get('/api/growth/mesocycle/?weeks=2&days_per_week=2')
        exercises = [
            exercise
            for week in response.data['weeks']
            for session in week['sessions']
            for slot in session['slots']
            for exercise in slot['exercises']
        ]
        self.assertTrue(exercises)
        self.assertTrue(all(item['sets'] > 0 for item in exercises))
        self.assertTrue(all(item['reps'] > 0 for item in exercises))

    def test_mesocycle_exercise_catalog_is_indexed_by_muscle(self):
        from .services import exercise_catalog

        Exercise.objects.create(
            name="杠铃深蹲", description="腿部动作", target_muscle="legs", instructions="蹲到大腿平行"
        )
        catalog = exercise_catalog()
        self.assertIn('legs', catalog)
        self.assertEqual(catalog['legs'][0]['name'], '杠铃深蹲')
        self.assertIn('exercise_id', catalog['legs'][0])

    def test_e1rm_is_saved_as_a_personal_record(self):
        bench = Exercise.objects.create(
            name="杠铃卧推", description="胸部力量动作", target_muscle="chest"
        )
        session = UserTrainingSession.objects.create(
            user=self.user,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=20),
            is_completed=True,
            total_exercises=1,
            completed_exercises=1,
            performance_score=4.0,
        )
        UserTrainingExerciseRecord.objects.create(
            session=session,
            exercise=bench,
            sets_completed=1,
            reps_completed=[5],
            weights_used=[100.0],
            form_score=90,
        )
        update_personal_records(session)

        record = PersonalRecord.objects.get(
            user=self.user, exercise=bench, record_type="e1rm"
        )
        self.assertGreater(record.value, 100.0)

    def test_load_curve_endpoint(self):
        for offset in range(0, 12, 2):
            self._api_session(offset=offset)

        response = self.client.get('/api/growth/load-curve/?days=30&step=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['days'], 30)
        self.assertEqual(response.data['step'], 2)
        self.assertEqual(len(response.data['points']), 15)
        self.assertIn('tsb', response.data['points'][-1])

    def test_load_curve_clamps_its_query_params(self):
        response = self.client.get('/api/growth/load-curve/?days=9999&step=abc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['days'], 180)
        self.assertEqual(response.data['step'], 1)

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



class QueryCountTests(TestCase):
    """查询次数回归测试。

    成长体系的总览接口每次都要跑一遍指标聚合与成就判定，
    这里断言"查询次数不随数据量线性增长"—— 挡住新引入的 N+1。
    """

    def setUp(self):
        self.client = APIClient()

    def _make_user(self, username):
        user = User.objects.create_user(username=username, password="StrongPass123")
        self.client.force_authenticate(user)
        return user

    def _seed(self, user, sessions=6, exercises=4):
        for index in range(exercises):
            Exercise.objects.create(
                name=f"动作 {username_seed(index)}",
                description="性能测试用",
                target_muscle="chest" if index % 2 == 0 else "back",
                instructions="标准姿势",
            )
        exercise_ids = list(Exercise.objects.values_list("id", flat=True))
        for index in range(sessions):
            start = timezone.now() - timedelta(days=index, minutes=5)
            session = UserTrainingSession.objects.create(
                user=user,
                start_time=start,
                end_time=start + timedelta(minutes=30),
                is_completed=True,
                total_exercises=len(exercise_ids),
                completed_exercises=len(exercise_ids),
                calories_burned=200,
                performance_score=4.0,
            )
            for exercise_id in exercise_ids:
                UserTrainingExerciseRecord.objects.create(
                    session=session,
                    exercise_id=exercise_id,
                    sets_completed=3,
                    reps_completed=[10, 10, 10],
                    weights_used=[40.0, 40.0, 40.0],
                    form_score=88,
                )
        return exercise_ids

    def _count_overview_queries(self, user):
        """统计总览接口的查询次数（先跑一次让状态稳定，再计数）。"""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.client.force_authenticate(user)
        self.client.get("/api/growth/overview/")
        with CaptureQueriesContext(connection) as captured:
            self.client.get("/api/growth/overview/")
        return len(captured.captured_queries)

    def test_overview_query_count_does_not_grow_with_the_data(self):
        small = self._make_user("query_small")
        self._seed(small, sessions=4, exercises=3)
        small_count = self._count_overview_queries(small)

        large = self._make_user("query_large")
        self._seed(large, sessions=12, exercises=8)
        large_count = self._count_overview_queries(large)

        # 数据量翻了三倍，查询次数不应该跟着涨。
        self.assertLessEqual(large_count, small_count + 2)

    def test_personal_record_update_reads_the_existing_records_once(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from .services import update_personal_records

        user = self._make_user("query_records")
        self._seed(user, sessions=1, exercises=5)
        session = UserTrainingSession.objects.filter(user=user).first()
        PersonalRecord.objects.filter(user=user).delete()

        with CaptureQueriesContext(connection) as captured:
            update_personal_records(session)

        selects = [
            item
            for item in captured.captured_queries
            if item["sql"].lstrip().upper().startswith("SELECT")
        ]
        # 读取既有纪录只查一次；其余都是写入。
        self.assertLessEqual(len(selects), 2)

    def test_achievement_evaluation_reads_the_unlocked_set_once(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from .services import evaluate_achievements

        user = self._make_user("query_achievements")
        self._seed(user, sessions=5, exercises=3)
        Achievement.objects.filter(is_active=True).delete()
        for index in range(12):
            Achievement.objects.create(
                code=f"perf_{index}",
                title=f"性能成就 {index}",
                description="查询次数测试",
                metric="sessions",
                threshold=index,
                xp_reward=10,
                is_active=True,
            )

        with CaptureQueriesContext(connection) as captured:
            evaluate_achievements(user)

        # "是否已解锁"只查一次，而不是每个成就查一次。
        unlocked_checks = [
            item
            for item in captured.captured_queries
            if "growth_userachievement" in item["sql"] and "achievement_id" in item["sql"]
        ]
        self.assertLessEqual(len(unlocked_checks), 2)


def username_seed(index: int) -> str:
    """给动作名加后缀，避免同一测试里重名。"""
    return f"{index}-{timezone.now().timestamp()}"
