# core/tests/test_profile.py
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Identity


class ProfileAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username="user1", password="pass123")
        cls.u2 = User.objects.create_user(username="user2", password="pass123")

        cls.i_u1 = Identity.objects.create(
            user=cls.u1, display_name="u1 Legal", context="Legal", language="en"
        )
        cls.i_u2 = Identity.objects.create(
            user=cls.u2, display_name="u2 Work", context="Work", language="zh"
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.u1)

    def test_get_me_profile(self):
        r = self.client.get("/api/me/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()["username"], "user1")

    def test_update_profile_basic_fields_and_url_normalization(self):
        payload = {
            "display_label": "Jonathan",
            "bio": "Hello",
            "gender_identity": "Male",
            "pronouns": "He/Him",
            "website": "www.google.com",  # should normalize to https://www.google.com
            "linkedin": "linkedin.com/in/test",  # normalize too
        }
        r = self.client.patch("/api/me/profile/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data["display_label"], "Jonathan")
        self.assertTrue(data["website"].startswith("http"))
        self.assertTrue(data["linkedin"].startswith("http"))

    def test_set_preferred_identity_to_own(self):
        r = self.client.patch("/api/me/profile/", {"preferred_identity": self.i_u1.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json().get("preferred_identity"), self.i_u1.id)

    def test_cannot_set_preferred_identity_to_others(self):
        r = self.client.patch("/api/me/profile/", {"preferred_identity": self.i_u2.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_profile_fallback_and_then_preferred(self):
        # initially no preferred_identity; display label is empty too
        r1 = self.client.get("/api/profile/user1/")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.client.patch("/api/me/profile/", {"display_label": "MyLabel"}, format="json")
        r2 = self.client.get("/api/profile/user1/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.json().get("preferred_identity_name"), None)

        self.client.patch("/api/me/profile/", {"preferred_identity": self.i_u1.id}, format="json")
        r3 = self.client.get("/api/profile/user1/")
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertEqual(r3.json().get("preferred_identity_name"), "u1 Legal")
        self.assertIn("preferred_identity_data", r3.json())
        self.assertEqual(r3.json()["preferred_identity_data"]["context"], "Legal")
