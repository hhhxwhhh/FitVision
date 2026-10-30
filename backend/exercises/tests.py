from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Exercise, ExerciseCategory


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
