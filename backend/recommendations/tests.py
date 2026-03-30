from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch

from exercises.models import Exercise, ExerciseCategory
from recommendations.models import RecommendedExercise, UserInteraction, UserState
from recommendations.serializers import RecommendedExerciseSerializer


class RecommendationSerializerModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rec_tester", password="pwd123456"
        )
        category = ExerciseCategory.objects.create(name="测试分类")
        self.exercise = Exercise.objects.create(
            name="测试深蹲",
            english_name="Test Squat",
            description="测试动作描述",
            category=category,
            difficulty="beginner",
            equipment="none",
            target_muscle="legs",
            instructions="动作要领",
            tips="注意事项",
            image_url="https://example.com/test.png",
        )
        self.rec = RecommendedExercise.objects.create(
            user=self.user,
            exercise=self.exercise,
            algorithm="default:cosine",
            score=0.8,
            rank=1,
            reason="测试推荐理由",
        )

    def test_brief_mode_returns_lightweight_exercise_fields(self):
        data = RecommendedExerciseSerializer(self.rec, context={"brief": True}).data
        self.assertIn("exercise", data)
        self.assertIn("difficulty", data["exercise"])
        self.assertIn("target_muscle", data["exercise"])
        # 轻量模式下不应包含完整详情字段
        self.assertNotIn("instructions", data["exercise"])

    def test_full_mode_returns_full_exercise_fields(self):
        data = RecommendedExerciseSerializer(self.rec, context={"brief": False}).data
        self.assertIn("exercise", data)
        self.assertIn("instructions", data["exercise"])
        self.assertIn("description", data["exercise"])


class RecommendationViewSetActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="rec_api_tester", password="pwd123456"
        )
        self.client.force_authenticate(user=self.user)

        category = ExerciseCategory.objects.create(name="接口测试分类")
        self.exercise = Exercise.objects.create(
            name="接口测试动作",
            english_name="API Test Exercise",
            description="接口测试动作描述",
            category=category,
            difficulty="beginner",
            equipment="none",
            target_muscle="legs",
            instructions="动作要领",
            tips="注意事项",
            image_url="https://example.com/api.png",
        )

        self.rec = RecommendedExercise.objects.create(
            user=self.user,
            exercise=self.exercise,
            algorithm="default:cosine",
            score=0.9,
            rank=1,
            reason="接口测试推荐理由",
        )

    @patch("recommendations.views.HybridRecommender.get_recommendations")
    def test_get_personalized_limit_and_brief(self, mocked_get_recommendations):
        mocked_get_recommendations.return_value = [self.rec]

        response = self.client.get(
            "/api/recommendations/list/get_personalized/?limit=1&brief=1"
        )

        self.assertEqual(response.status_code, 200)
        mocked_get_recommendations.assert_called_once_with(
            self.user, scenario="default", limit=1
        )
        self.assertEqual(len(response.data), 1)
        self.assertNotIn("instructions", response.data[0]["exercise"])

    @patch("recommendations.views.HybridRecommender.get_recommendations")
    def test_get_personalized_invalid_limit_fallbacks_to_default(self, mocked_get):
        mocked_get.return_value = [self.rec]

        response = self.client.get(
            "/api/recommendations/list/get_personalized/?limit=abc&brief=0"
        )

        self.assertEqual(response.status_code, 200)
        mocked_get.assert_called_once_with(self.user, scenario="default", limit=6)
        self.assertIn("instructions", response.data[0]["exercise"])

    @patch("recommendations.views.cache")
    def test_user_status_hits_cache_and_feedback_clears_cache(self, mocked_cache):
        mocked_cache.get.return_value = {"fatigue_level": 0.77, "cached": True}

        status_resp = self.client.get("/api/recommendations/list/user_status/")
        self.assertEqual(status_resp.status_code, 200)
        self.assertTrue(status_resp.data["cached"])
        self.assertEqual(UserState.objects.filter(user=self.user).count(), 0)

        feedback_resp = self.client.post(
            f"/api/recommendations/list/{self.rec.id}/feedback/", {"action": "like"}
        )
        self.assertEqual(feedback_resp.status_code, 200)
        mocked_cache.delete.assert_called_once_with(f"rec_user_status:{self.user.id}")

        self.rec.refresh_from_db()
        self.assertTrue(self.rec.is_seen)
        self.assertEqual(
            UserInteraction.objects.filter(
                user=self.user, exercise=self.exercise, interaction_type="like"
            ).count(),
            1,
        )
