from django.test import TestCase
from django.contrib.auth.models import User

from exercises.models import Exercise, ExerciseCategory
from recommendations.models import RecommendedExercise
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
