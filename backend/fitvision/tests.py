from django.test import TestCase
from rest_framework import status


class HealthEndpointTests(TestCase):
    def test_health_reports_ok(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")
        self.assertTrue(response.data["checks"]["database"])
        self.assertTrue(response.data["checks"]["cache"])

    def test_api_index_exposes_docs_links(self):
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("docs", response.data)
        self.assertIn("health", response.data)
