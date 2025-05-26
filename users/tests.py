from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import User


class UserTests(APITestCase):
    def setUp(self):
        # Create groups
        self.student_group = Group.objects.get_or_create(name="student")[0]
        self.teacher_group = Group.objects.get_or_create(name="teacher")[0]
        self.manager_group = Group.objects.get_or_create(name="manager")[0]
        self.admin_group = Group.objects.get_or_create(name="admin")[0]

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@admin.com",
            password="admin",
            national_id="1111111111",
        )

        # Create a normal user
        self.user = User.objects.create_user(
            username="user",
            email="user@user.com",
            password="user",
            national_id="2222222222",
        )

        # URLs
        self.registration_url = reverse("userregistrationview")
        self.user_list_url = reverse("user-list")

    def authenticate_as_user(self):
        self.client.force_authenticate(user=self.user)

    def authenticate_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def test_register_user_successfully(self):
        data = {
            "username": "a",
            "email": "a@b.com",
            "password": "a",
            "confirm_password": "a",
            "first_name": "a",
            "last_name": "b",
            "national_id": "1234567890",
            "group": "student",
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)
        self.assertTrue(User.objects.filter(username="a").exists())

    def test_register_existing_user_adds_group(self):
        response = self.client.post(
            self.registration_url,
            {
                "national_id": self.user.national_id,
                "group": "teacher",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.groups.filter(name="teacher").exists())

    def test_register_invalid_national_id(self):
        data = {
            "username": "ab",
            "email": "ab@a.com",
            "password": "a",
            "confirm_password": "a",
            "first_name": "ad",
            "last_name": "af",
            "national_id": "345",
            "group": "student",
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Your national id must be 10 digits", str(response.data))

    def test_register_mismatched_passwords(self):
        data = {
            "username": "df",
            "email": "df@g.com",
            "password": "d",
            "confirm_password": "df",
            "first_name": "df",
            "last_name": "df",
            "national_id": "1234567890",
            "group": "student",
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Password does not match", str(response.data))

    def test_user_cannot_activate(self):
        self.authenticate_as_user()
        url = reverse("user-activate", kwargs={"pk": self.user.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_activate_user(self):
        self.authenticate_as_admin()
        user_to_activate = User.objects.create_user(
            username="h",
            email="h@q.com",
            password="q",
            national_id="9999999999",
        )
        url = reverse("user-activate", kwargs={"pk": user_to_activate.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_to_activate.refresh_from_db()
        self.assertTrue(user_to_activate.is_active)
