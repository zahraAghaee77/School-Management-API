from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Class, School

User = get_user_model()


#   you should work on it
class SchoolViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manager",
            password="m",
            email="a@b.com",
            national_id="1234567890",
        )
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@admin.com",
            password="admin",
            national_id="1111111111",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.school = School.objects.create(
            name="Test School",
            manager=self.user,
            location=Point(10.0, 20.0),
        )

    def authenticate_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def test_list_schools(self):
        url = reverse("school-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_school(self):
        url = reverse("school-list")
        self.authenticate_as_admin()
        user = User.objects.create_user(
            username="manager1",
            password="m",
            email="avv@b.com",
            national_id="1234567790",
        )
        manager_group, _ = Group.objects.get_or_create(name="manager")
        user.groups.add(manager_group)
        data = {
            "name": "New School",
            "manager": user.id,
            "location": {"type": "Point", "coordinates": [15.0, 25.0]},
        }
        response = self.client.post(url, data, format="json")
        properties = response.data["properties"]
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["properties"]["name"], "New School")

    def test_retrieve_school(self):
        self.authenticate_as_admin()
        url = reverse("school-detail", args=[self.school.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], self.school.name)

    def test_update_school(self):
        self.authenticate_as_admin()
        url = reverse("school-detail", args=[self.school.id])
        data = {"name": "Updated School"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], "Updated School")

    def test_delete_school(self):
        self.authenticate_as_admin()
        url = reverse("school-detail", args=[self.school.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(School.objects.filter(id=self.school.id).exists())

    def test_nearby_schools(self):
        manager1 = User.objects.create_user(
            username="manager1",
            password="pass1234",
            email="avv@b.com",
            national_id="1234567790",
        )
        manager2 = User.objects.create_user(
            username="manager2",
            password="pass1234",
            email="avdv@b.com",
            national_id="1234567793",
        )
        manager3 = User.objects.create_user(
            username="manager3",
            password="pass1234",
            email="avvg@b.com",
            national_id="1234567792",
        )
        manager4 = User.objects.create_user(
            username="manager4",
            password="pass1234",
            email="avva@b.com",
            national_id="1234567791",
        )
        School.objects.create(
            name="Far",
            manager=manager1,
            location=Point(10.0, 21.0),
        )
        School.objects.create(
            name="Pretty Far", manager=manager2, location=Point(10, 20.1)
        )
        School.objects.create(
            name="Pretty so Far", manager=manager3, location=Point(10, 20.01)
        )
        School.objects.create(
            name="Pretty so much Far", manager=manager4, location=Point(10, 20.001)
        )
        url = reverse("school-nearby")
        data = {"lng": 10.0002, "lat": 20.0, "radius_km": 1000}
        response = self.client.post(url, data, format="json")
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s["name"] for s in response.data]
        self.assertIn(self.school.name, names)
        self.assertNotIn("Far School", names)

    def test_invalid_input_nearby(self):
        url = reverse("school-nearby")
        data = {"lng": "er", "lat": 20.0, "radius_km": 1000}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_parameter_nearby(self):
        url = reverse("school-nearby")
        data = {"lng": "er", "radius_km": 1000}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sorted_distance_nearby(self):
        url = reverse("school-nearby")
        data = {"lng": 10.0002, "lat": 20.0, "radius_km": 5000}
        manager1 = User.objects.create_user(
            username="manager1",
            password="pass1234",
            email="avv@b.com",
            national_id="1234567790",
        )
        far_school = School.objects.create(
            name="Far",
            manager=manager1,
            location=Point(10.0, 20.02),
        )
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # print(response.data)
        names = [s["name"] for s in response.data]
        self.assertIn(self.school.name, names)
        self.assertNotIn("Far School", names)
        self.assertEqual(names[0], self.school.name)
        self.assertEqual(names[1], far_school.name)


class ClassViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="teacher",
            password="t",
            email="av@b.com",
            national_id="1134567890",
        )
        gr, _ = Group.objects.get_or_create(name="teacher")
        self.user.groups.add(gr)
        self.student = User.objects.create_user(
            username="student",
            password="s",
            email="ab@b.com",
            national_id="1233567890",
        )
        gr, _ = Group.objects.get_or_create(name="student")
        self.student.groups.add(gr)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@admin.com",
            password="admin",
            national_id="1111111111",
        )

        self.school = School.objects.create(
            name="Test School",
            manager=self.user,
            location=Point(10.0, 20.0),
        )
        self.classroom = Class.objects.create(
            name="Test Class",
            school=self.school,
            teacher=self.user,
        )

    def authenticate_as_user(self):
        self.client.force_authenticate(user=self.user)

    def authenticate_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def test_list_classes(self):
        url = reverse("class-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_class(self):
        self.authenticate_as_admin()
        url = reverse("class-list")
        data = {
            "name": "New Class",
            "school": self.school.id,
            "teacher": self.user.id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Class")

    def test_retrieve_class(self):
        url = reverse("class-detail", args=[self.classroom.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.classroom.name)

    def test_update_class(self):
        self.authenticate_as_admin()
        url = reverse("class-detail", args=[self.classroom.id])
        data = {"name": "Updated Class"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Class")

    def test_delete_class(self):
        self.authenticate_as_admin()
        url = reverse("class-detail", args=[self.classroom.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Class.objects.filter(id=self.classroom.id).exists())

    def test_add_students(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("class-add-student", args=[self.classroom.id])
        response = self.client.post(
            url, data={"national_id": self.student.national_id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
