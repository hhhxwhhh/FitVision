from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthAPITests(APITestCase):
    def test_register_creates_user_and_profile(self):
        response = self.client.post(
            reverse("register"),
            {"username": "alice", "password": "s3cret-pass", "password_confirm": "s3cret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="alice")
        self.assertTrue(user.check_password("s3cret-pass"))
        # The post_save signal should provision a UserProfile.
        self.assertTrue(hasattr(user, "profile"))

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("register"),
            {"username": "bob", "password": "s3cret-pass", "password_confirm": "different"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="bob").exists())

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("register"),
            {"username": "weakuser", "password": "12345678", "password_confirm": "12345678"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="weakuser").exists())

    def test_refresh_returns_new_access_token(self):
        User.objects.create_user(username="frank", password="s3cret-pass")
        login = self.client.post(
            reverse("login"),
            {"username": "frank", "password": "s3cret-pass"},
            format="json",
        )

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_returns_jwt_tokens(self):
        User.objects.create_user(username="carol", password="s3cret-pass")

        response = self.client.post(
            reverse("login"),
            {"username": "carol", "password": "s3cret-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_bad_credentials(self):
        User.objects.create_user(username="dave", password="s3cret-pass")

        response = self.client.post(
            reverse("login"),
            {"username": "dave", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        user = User.objects.create_user(username="erin", password="s3cret-pass")
        profile = user.profile
        profile.nickname = "Erin"
        profile.save()
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "erin")
        self.assertEqual(response.data["nickname"], "Erin")
