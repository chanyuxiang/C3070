
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Identity


class IdentityAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # User1
        cls.u1 = User.objects.create_user(username="user1", password="pass123")
        # User2
        cls.u2 = User.objects.create_user(username="user2", password="pass123")
        # Admin 
        cls.admin = User.objects.create_superuser(
            username="admin", password="adminpass", email="a@a.com"
        )

        # seed identities
        cls.i1_u1 = Identity.objects.create(
            user=cls.u1, display_name="u1 Legal", context="Legal", language="en"
        )
        cls.i2_u1 = Identity.objects.create(
            user=cls.u1, display_name="u1 School", context="School", language="en"
        )
        cls.i1_u2 = Identity.objects.create(
            user=cls.u2, display_name="u2 Work", context="Work", language="zh"
        )

    def setUp(self):
        self.client = APIClient()

    # ---------- list / create ----------

    def test_list_identities_user_sees_only_own(self):
        self.client.force_authenticate(self.u1)
        r = self.client.get("/api/identities/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.json()), 2)  # u1's two identities
        names = {x["display_name"] for x in r.json()}
        self.assertSetEqual(names, {"u1 Legal", "u1 School"})

    def test_list_identities_admin_sees_all(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/identities/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.json()), 3)

    def test_create_identity(self):
        self.client.force_authenticate(self.u1)
        payload = {"display_name": "New One", "context": "Gaming", "language": "ms"}
        r = self.client.post("/api/identities/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Identity.objects.filter(user=self.u1, display_name="New One").exists())

    # ---------- update / delete / permissions ----------

    def test_user_can_update_own_identity(self):
        self.client.force_authenticate(self.u1)
        r = self.client.put(
            f"/api/identities/{self.i1_u1.id}/",
            {"display_name": "Updated", "context": "Legal", "language": "en"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.i1_u1.refresh_from_db()
        self.assertEqual(self.i1_u1.display_name, "Updated")

    def test_user_cannot_update_others_identity(self):
        self.client.force_authenticate(self.u1)
        r = self.client.put(
            f"/api/identities/{self.i1_u2.id}/",
            {"display_name": "HACK", "context": "Work", "language": "en"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_own_identity(self):
        self.client.force_authenticate(self.u1)
        r = self.client.delete(f"/api/identities/{self.i2_u1.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Identity.objects.filter(id=self.i2_u1.id).exists())
