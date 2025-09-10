
import json
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Identity


class ImportExportTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username="user1", password="pass123")
        Identity.objects.create(user=cls.u1, display_name="Legal EN", context="Legal", language="en")
        Identity.objects.create(user=cls.u1, display_name="School ZH", context="School", language="zh")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.u1)

    def test_export_json_format(self):
        r = self.client.get("/api/identities/export/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r["Content-Disposition"].startswith('attachment;'), True)
        payload = r.json()
        self.assertIn("items", payload)
        self.assertEqual(len(payload["items"]), 2)

    def test_import_valid_items(self):
        payload = {
            "items": [
                {"display_name": "Gaming Nick", "context": "Gaming", "language": "ms"},
                {"display_name": "Religious Name", "context": "Religious", "language": "ta"},
            ]
        }
        r = self.client.post("/api/identities/import/", payload, format="json")
        self.assertIn(r.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))
        self.assertTrue(Identity.objects.filter(user=self.u1, display_name="Gaming Nick").exists())
        self.assertTrue(Identity.objects.filter(user=self.u1, display_name="Religious Name").exists())

    def test_import_rejects_missing_display_name(self):
        payload = {"items": [{"context": "Work", "language": "en"}]}
        r = self.client.post("/api/identities/import/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        body = r.json()
        self.assertIn("errors", body)
        self.assertTrue(any("display_name" in e for e in body["errors"]))

    def test_import_via_multipart_file(self):
        body = {
            "items": [
                {"display_name": "FileNick", "context": "Work", "language": "en"},
            ]
        }
        content = json.dumps(body).encode("utf-8")
        # DRF test client needs (fieldname, fileobj, content_type)
        from io import BytesIO
        file_tuple = ("file", BytesIO(content), "application/json")
        r = self.client.post("/api/identities/import/", {"file": file_tuple}, format="multipart")
        self.assertIn(r.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))
        self.assertTrue(Identity.objects.filter(user=self.u1, display_name="FileNick").exists())
