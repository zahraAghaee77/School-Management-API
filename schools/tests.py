from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from schools.models import Class, Lesson, School
from users.models import User


class SchoolActionsTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create user groups
        self.teacher_group = Group.objects.create(name="teacher")
        self.student_group = Group.objects.create(name="student")
        self.manager_group = Group.objects.create(name="manager")
        self.admin_group = Group.objects.create(name="admin")

        # Create users
        self.admin_user = User.objects.create_superuser(
            username="admin", password="testpass123", email="admin@a.com"
        )
        self.manager_user = User.objects.create_user(
            username="manager",
            password="testpass123",
            email="admin@af.com",
            national_id="1234567890",
        )
        self.manager_user.groups.add(self.manager_group)

        self.teacher_user = User.objects.create_user(
            username="teacher",
            password="testpass123",
            email="admin@ab.com",
            national_id="1234567870",
        )
        self.teacher_user.groups.add(self.teacher_group)

        self.student_user = User.objects.create_user(
            username="student",
            password="testpass123",
            email="admin@ac.com",
            national_id="1234367890",
        )
        self.student_user.groups.add(self.student_group)

        # Create school
        self.school = School.objects.create(
            name="Test School",
            manager=self.manager_user,
            location=Point(-73.994454, 40.750042),
        )

        # Create class
        self.classroom = Class.objects.create(
            name="Math 101", school=self.school, teacher=self.teacher_user
        )
        self.classroom.students.add(self.student_user)

        # Create lesson (optional)
        self.lesson = Lesson.objects.create(
            title="Intro to Algebra", class_lessons=self.classroom
        )

        # URLs
        self.base_url = reverse("school-detail", kwargs={"pk": self.school.id})

    def _get_action_url(self, action):
        return f"{self.base_url}{action}/"

    def test_manager_can_access_all_school_actions(self):
        self.client.force_authenticate(user=self.manager_user)

        actions = ["students", "teachers", "classes", "lessons"]
        for action in actions:
            url = self._get_action_url(action)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_only_managers_can_access_school_actions(self):
        actions = ["students", "teachers", "classes", "lessons"]

        for action in actions:
            url = self._get_action_url(action)

            # Try as admin
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Try as teacher
            self.client.force_authenticate(user=self.teacher_user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Try as student
            self.client.force_authenticate(user=self.student_user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_students_action_returns_correct_users(self):
        self.client.force_authenticate(user=self.manager_user)
        url = self._get_action_url("students")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [user["username"] for user in response.data]
        self.assertIn(self.student_user.username, usernames)

    def test_teachers_action_returns_correct_users(self):
        self.client.force_authenticate(user=self.manager_user)
        url = self._get_action_url("teachers")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [user["username"] for user in response.data]
        self.assertIn(self.teacher_user.username, usernames)

    def test_classes_action_returns_correct_classes(self):
        self.client.force_authenticate(user=self.manager_user)
        url = self._get_action_url("classes")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        class_names = [cls["name"] for cls in response.data]
        self.assertIn(self.classes.name, class_names)

    def test_lessons_action_returns_correct_lessons(self):
        self.client.force_authenticate(user=self.manager_user)
        url = self._get_action_url("lessons")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [lesson["title"] for lesson in response.data]
        self.assertIn(self.classes.lessons.title, titles)

    def test_unauthorized_access_to_school_actions_fails(self):
        self.client.logout()
        actions = ["students", "teachers", "classes", "lessons"]
        for action in actions:
            url = self._get_action_url(action)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_school_id_returns_404(self):
        self.client.force_authenticate(user=self.manager_user)
        invalid_url_base = reverse("school-detail", kwargs={"pk": 999})

        actions = ["students", "teachers", "classes", "lessons"]
        for action in actions:
            url = f"{invalid_url_base}{action}/"
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_cannot_manage_multiple_schools(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "Second School",
            "location": {"type": "Point", "coordinates": [-73.994454, 40.750042]},
            "manager": self.manager_user.id,
        }

        response = self.client.post(reverse("school-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("manager", response.data)
        self.assertEqual(
            str(response.data["manager"][0]),
            "This user is already a manager of another school.",
        )
