from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from training.models import TrainingPlan

from .models import Exercise, ExerciseCategory, UserExerciseRecord


class ExerciseAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gymfan", password="s3cret-pass")
        self.category = ExerciseCategory.objects.create(name="力量")
        self.exercise = Exercise.objects.create(
            name="深蹲",
            english_name="Squat",
            description="经典下肢训练动作",
            category=self.category,
            target_muscle="legs",
            difficulty="beginner",
            equipment="none",
            instructions="屈髋屈膝下蹲，保持背部中立。",
        )

    def test_list_requires_authentication(self):
        response = self.client.get(reverse("exercises"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_active_exercises(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("exercises"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "深蹲")

    def test_inactive_exercises_are_hidden(self):
        self.exercise.is_active = False
        self.exercise.save()
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("exercises"))

        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 0)

    def test_detail_returns_exercise(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("exercise-detail", args=[self.exercise.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "深蹲")


class SeedDemoCommandTests(TestCase):
    def test_seeds_exercises_and_plan_on_empty_database(self):
        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Exercise.objects.count(), 60)
        self.assertEqual(TrainingPlan.objects.count(), 1)
        plan = TrainingPlan.objects.get()
        self.assertIsNotNone(plan.created_by)

    def test_seed_is_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        user_count = User.objects.count()

        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Exercise.objects.count(), 60)
        self.assertEqual(TrainingPlan.objects.count(), 1)
        self.assertEqual(User.objects.count(), user_count)


class ExerciseQueryCountTests(TestCase):
    """动作列表的查询次数回归测试。

    列表接口曾经是"每个动作 5 次查询"（分类、前置、解锁、最好成绩、最近记录），
    现在靠 select_related / prefetch_related 收敛成常数次查询。
    """

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.user = User.objects.create_user(username="queryfan", password="s3cret-pass")
        self.client.force_authenticate(self.user)
        self.category = ExerciseCategory.objects.create(name="力量")

    def _seed(self, count):
        offset = Exercise.objects.count()
        for index in range(offset, offset + count):
            exercise = Exercise.objects.create(
                name=f"动作 {index}",
                description="性能测试用",
                category=self.category,
                target_muscle="chest" if index % 2 == 0 else "back",
                instructions="标准姿势",
            )
            UserExerciseRecord.objects.create(
                user=self.user,
                exercise=exercise,
                count=10,
                duration=60,
                accuracy_score=80 + index,
            )

    def _count_list_queries(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.client.get(reverse("exercises"))
        with CaptureQueriesContext(connection) as captured:
            self.client.get(reverse("exercises"))
        return len(captured.captured_queries)

    def test_list_query_count_does_not_grow_with_the_page_size(self):
        self._seed(3)
        small_count = self._count_list_queries()

        self._seed(12)
        large_count = self._count_list_queries()

        # 动作数量翻了几倍，查询次数不应该跟着涨。
        self.assertLessEqual(large_count, small_count + 2)
