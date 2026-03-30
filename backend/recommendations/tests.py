from django.test import TestCase
from django.contrib.auth.models import User
import random
from rest_framework.test import APIClient
from unittest.mock import patch

from exercises.models import Exercise, ExerciseCategory
from recommendations.models import RecommendedExercise, UserInteraction, UserState
from recommendations.serializers import (
    RecommendedExerciseSerializer,
    FeedbackActionSerializer,
)
from recommendations.services import HybridRecommender


class _DummyExercise:
    def __init__(
        self,
        ex_id,
        target_muscle="legs",
        equipment="none",
        calories_burned=5.0,
        tags=None,
    ):
        self.id = ex_id
        self.target_muscle = target_muscle
        self.equipment = equipment
        self.calories_burned = calories_burned
        self.tags = tags or []


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


class FeedbackActionSerializerTests(TestCase):
    def test_accepts_and_normalizes_action(self):
        serializer = FeedbackActionSerializer(data={"action": " LIKE "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["action"], "like")

    def test_rejects_invalid_action(self):
        serializer = FeedbackActionSerializer(data={"action": "oops"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("action", serializer.errors)


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

    @patch("recommendations.views.HybridRecommender.get_recommendations")
    def test_get_personalized_limit_above_max_is_clamped(self, mocked_get):
        mocked_get.return_value = [self.rec]

        response = self.client.get(
            "/api/recommendations/list/get_personalized/?limit=999&brief=1"
        )

        self.assertEqual(response.status_code, 200)
        mocked_get.assert_called_once_with(self.user, scenario="default", limit=20)

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

    @patch("recommendations.views.cache")
    def test_feedback_invalid_action_returns_400(self, mocked_cache):
        response = self.client.post(
            f"/api/recommendations/list/{self.rec.id}/feedback/", {"action": "oops"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("action", response.data)
        self.rec.refresh_from_db()
        self.assertFalse(self.rec.is_seen)
        self.assertEqual(UserInteraction.objects.filter(user=self.user).count(), 0)
        mocked_cache.delete.assert_not_called()


class HybridRecommenderStrategyTests(TestCase):
    def test_compute_exploration_ratio_increases_with_negative_feedback(self):
        low_ratio = HybridRecommender._compute_exploration_ratio(
            positive_count=20, negative_count=1
        )
        high_ratio = HybridRecommender._compute_exploration_ratio(
            positive_count=1, negative_count=20
        )
        self.assertLess(low_ratio, high_ratio)
        self.assertGreaterEqual(low_ratio, 0.08)
        self.assertLessEqual(high_ratio, 0.35)

    def test_select_with_exploration_keeps_top_and_adds_explore(self):
        candidates = [
            {
                "ex": _DummyExercise(ex_id=i, target_muscle="legs"),
                "score": 1.0 - (i * 0.05),
                "algorithm": "cosine",
            }
            for i in range(10)
        ]

        rng = random.Random(1234)
        selected = HybridRecommender._select_with_exploration(
            candidates=candidates,
            limit=6,
            exploration_ratio=0.33,
            rng=rng,
        )

        self.assertEqual(len(selected), 6)
        selected_ids = {item["ex"].id for item in selected}
        # 最高分候选应保留
        self.assertIn(0, selected_ids)
        # 应有至少一个不是纯前6名的探索候选
        self.assertTrue(any(ex_id >= 6 for ex_id in selected_ids))

    def test_goal_rerank_prefers_full_body_for_weight_loss(self):
        candidates = [
            {
                "ex": _DummyExercise(
                    ex_id=1,
                    target_muscle="legs",
                    equipment="dumbbell",
                    calories_burned=6.0,
                ),
                "score": 1.0,
                "algorithm": "cosine",
            },
            {
                "ex": _DummyExercise(
                    ex_id=2,
                    target_muscle="full_body",
                    equipment="none",
                    calories_burned=10.0,
                    tags=["cardio"],
                ),
                "score": 0.9,
                "algorithm": "cosine",
            },
        ]

        reranked = HybridRecommender._rerank_by_user_goal(
            candidates, goal_type="weight_loss"
        )
        self.assertEqual(reranked[0]["ex"].id, 2)

    def test_goal_rerank_prefers_strength_for_muscle_gain(self):
        candidates = [
            {
                "ex": _DummyExercise(
                    ex_id=3,
                    target_muscle="full_body",
                    equipment="none",
                    calories_burned=7.0,
                ),
                "score": 1.0,
                "algorithm": "cosine",
            },
            {
                "ex": _DummyExercise(
                    ex_id=4,
                    target_muscle="chest",
                    equipment="barbell",
                    calories_burned=7.0,
                    tags=["strength"],
                ),
                "score": 0.9,
                "algorithm": "cosine",
            },
        ]

        reranked = HybridRecommender._rerank_by_user_goal(
            candidates, goal_type="muscle_gain"
        )
        self.assertEqual(reranked[0]["ex"].id, 4)
