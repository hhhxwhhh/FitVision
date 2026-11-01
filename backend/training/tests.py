"""训练模块的 API 测试：动作记录（RIR / RPE）与智能计划的 e1RM 处方。"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch

from exercises.models import Exercise
from training.models import UserTrainingExerciseRecord, UserTrainingSession


class TrainingRecordApiTests(TestCase):
    """动作记录接口：接受 RIR / RPE，并做取值校验。"""

    def setUp(self):
        self.user = User.objects.create_user(username="recorder", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.exercise = Exercise.objects.create(
            name="杠铃卧推",
            description="胸部力量动作",
            target_muscle="chest",
            instructions="肩胛骨收紧",
        )
        self.session = UserTrainingSession.objects.create(
            user=self.user,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=20),
            is_completed=False,
            total_exercises=1,
            completed_exercises=0,
        )

    def _post(self, **overrides):
        payload = {
            "session_id": self.session.id,
            "exercise": self.exercise.id,
            "sets_completed": 3,
            "reps_completed": [10, 10, 8],
            "weights_used": [60, 60, 60],
            "form_score": 88,
        }
        payload.update(overrides)
        return self.client.post("/api/training/exercise-records/", payload, format="json")

    def test_records_are_saved(self):
        response = self._post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserTrainingExerciseRecord.objects.count(), 1)

    def test_rir_is_stored(self):
        response = self._post(rir=2)
        self.assertEqual(response.status_code, 201)
        record = UserTrainingExerciseRecord.objects.get()
        self.assertEqual(record.rir, 2)

    def test_rpe_is_stored(self):
        response = self._post(rpe=8)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserTrainingExerciseRecord.objects.get().rpe, 8.0)

    def test_out_of_range_rir_is_rejected(self):
        response = self._post(rir=9)
        self.assertEqual(response.status_code, 400)
        self.assertIn("rir", response.data)

    def test_out_of_range_rpe_is_rejected(self):
        response = self._post(rpe=12)
        self.assertEqual(response.status_code, 400)
        self.assertIn("rpe", response.data)

    def test_rir_is_optional(self):
        response = self._post()
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(UserTrainingExerciseRecord.objects.get().rir)

    def test_a_finished_session_rejects_new_records(self):
        self.session.is_completed = True
        self.session.save(update_fields=["is_completed"])
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_another_user_session_is_not_reachable(self):
        other = User.objects.create_user(username="other", password="StrongPass123")
        self.session.user = other
        self.session.save(update_fields=["user"])
        response = self._post()
        self.assertEqual(response.status_code, 404)


class SmartPlanPrescriptionTests(TestCase):
    """智能计划：用用户的 e1RM 折算出每个动作的建议重量。"""

    def setUp(self):
        self.user = User.objects.create_user(username="planner", password="StrongPass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.exercise = Exercise.objects.create(
            name="杠铃卧推",
            description="胸部力量动作",
            target_muscle="chest",
            instructions="肩胛骨收紧",
        )

    def _generate(self, payload=None):
        body = {"goal": "增肌", "level": "中级", "days": 1, "focus": "胸", "equipment": "杠铃"}
        body.update(payload or {})
        with patch(
            "training.services.SmartRecommendationService.generate_chain_plan",
            return_value=[self.exercise],
        ):
            return self.client.post("/api/training/plan/create_smart/", body, format="json")

    def test_a_trained_exercise_gets_a_prescribed_weight(self):
        with patch(
            "growth.services.strength_history",
            return_value=[{"exercise_id": self.exercise.id, "best": 100.0}],
        ):
            response = self._generate()
        self.assertEqual(response.status_code, 200)
        exercise = response.data["weekly_schedule"][0]["exercises"][0]
        self.assertTrue(exercise["based_on_e1rm"])
        self.assertGreater(exercise["weight"], 0)
        self.assertAlmostEqual(exercise["e1rm"], 100.0)

    def test_an_untrained_exercise_has_no_weight(self):
        with patch("growth.services.strength_history", return_value=[]):
            response = self._generate()
        exercise = response.data["weekly_schedule"][0]["exercises"][0]
        self.assertFalse(exercise["based_on_e1rm"])
        self.assertEqual(exercise["weight"], 0)

    def test_a_broken_strength_model_does_not_break_the_plan(self):
        with patch("growth.services.strength_history", side_effect=RuntimeError("boom")):
            response = self._generate()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["weekly_schedule"][0]["exercises"][0]["based_on_e1rm"] is False)

    def test_the_plan_reports_the_readiness_block(self):
        response = self._generate()
        self.assertIn("readiness", response.data)
        self.assertIn("volume_multiplier", response.data["readiness"])
