from django.contrib.auth import get_user_model
from django.contrib.auth.models import *
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from assignments.models import Assignment, Solution
from assignments.permissions import CanGradeSolution
from assignments.views import SolutionViewSet
from schools.models import *

from .permissions import is_in_group

User = get_user_model()


class CanGradeSolutionPermissionTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        # Create users
        self.teacher_user = User.objects.create_user(
            username="teacher",
            password="testpass123",
            email="a@gmail.com",
            national_id="1234567890",
        )
        self.teacher_user.groups.set([Group.objects.get_or_create(name="teacher")[0]])

        self.manager_user = User.objects.create_user(
            username="manager",
            password="testpass123",
            email="ab@gmail.com",
            national_id="1234597890",
        )
        self.manager_user.groups.set([Group.objects.get_or_create(name="manager")[0]])

        self.student_user = User.objects.create_user(
            username="student",
            password="testpass123",
            email="da@gmail.com",
            national_id="1233367890",
        )
        self.student_user.groups.set([Group.objects.get_or_create(name="student")[0]])

        # Create school
        self.school = School.objects.create(
            name="Test School",
            manager=self.manager_user,
            location=Point(-73.994454, 40.750042),
        )

        # Create lesson
        self.lesson = Lesson.objects.create(name="Math")

        # Create class
        self.classroom = Class.objects.create(
            name="Math 101", teacher=self.teacher_user, school=self.school
        )

        # Create assignment (deadline in past)
        self.assignment = Assignment.objects.create(
            title="Homework",
            context="Do exercises.",
            deadline=timezone.now().date() - timezone.timedelta(days=1),
            class_obj=self.classroom,
            lesson=self.lesson,
            grade=50,
        )

        # Create solution
        self.solution = Solution.objects.create(
            context="My submission.",
            student=self.student_user,
            assignment=self.assignment,
        )

        # Set up request
        self.view = SolutionViewSet()
        self.view.action = "grade"

    def test_teacher_can_grade_after_deadline(self):
        perm = CanGradeSolution()
        request = self.factory.get("/fake-url")
        request.user = self.teacher_user

        # Patch viewset to return this request user
        self.view.request = type("Request", (object,), {"user": self.teacher_user})

        # Should allow grading if deadline passed
        self.assertTrue(perm.has_object_permission(request, self.view, self.solution))

    def test_teacher_cannot_grade_before_deadline(self):
        # Update assignment deadline to future
        self.assignment.deadline = timezone.now().date() + timezone.timedelta(days=7)
        self.assignment.save()

        perm = CanGradeSolution()
        request = self.factory.get("/fake-url")
        request.user = self.teacher_user
        self.view.request = type("Request", (object,), {"user": self.teacher_user})

        # Should NOT allow grading before deadline
        self.assertFalse(perm.has_object_permission(request, self.view, self.solution))

    def test_manager_can_not_grade_solution(self):
        # Update assignment deadline to past
        self.assignment.deadline = timezone.now().date() - timezone.timedelta(days=1)
        self.assignment.save()

        perm = CanGradeSolution()
        request = self.factory.get("/fake-url")
        request.user = self.manager_user
        self.view.request = type("Request", (object,), {"user": self.manager_user})

        # Ensure manager has access to the school
        self.assertTrue(
            not perm.has_object_permission(request, self.view, self.solution)
        )

    def test_student_cannot_grade_solution(self):
        perm = CanGradeSolution()
        request = self.factory.get("/fake-url")
        request.user = self.student_user
        self.view.request = type("Request", (object,), {"user": self.student_user})

        self.assertFalse(perm.has_object_permission(request, self.view, self.solution))

    def test_get_queryset_allows_teacher_to_see_solution(self):

        # Make sure solution exists and belongs to teacher's class
        solution = Solution.objects.create(
            context="My submission",
            student=self.student_user,
            assignment=self.assignment,  # Ensure future_assignment.class_obj.teacher == self.teacher_user
        )

        viewset = SolutionViewSet()
        viewset.request = type("Request", (), {"user": self.teacher_user})

        queryset = viewset.get_queryset()
        solution_in_queryset = queryset.filter(id=solution.id).exists()

        self.assertTrue(solution_in_queryset)

    from assignments.permissions import CanGradeSolution

    def test_can_grade_solution_permission_allows_access(self):

        solution = Solution.objects.create(
            context="Submitted on time.",
            student=self.student_user,
            assignment=self.assignment,  # Must belong to teacher's class
        )

        perm = CanGradeSolution()
        request = self.factory.post("/fake-url", {"grade": 90})
        request.user = self.teacher_user
        view = SolutionViewSet()
        view.kwargs = {"pk": solution.id}
        view.request = request

        result = perm.has_object_permission(request, view, solution)
        print("Has object permission:", result)
        self.assertTrue(result)

    def test_grading_api_endpoint(self):
        url = reverse("solution-detail", kwargs={"pk": self.solution.id})
        print(url)
        grade_url = f"{url}grade/"
        print("Solution exists:", Solution.objects.filter(id=self.solution.id).exists())
        print("URL generated:", grade_url)
        print(self.teacher_user)
        solu = Solution.objects.filter(id=self.solution.id)
        print(solu)
        # Try as teacher — should work after deadline
        self.client.force_login(self.teacher_user)
        response = self.client.post(grade_url, {"grade": 85})
        print("Solution exists:", Solution.objects.filter(id=self.solution.id).exists())
        print(
            "Assignment class teacher:",
            self.solution.assignment.class_obj.teacher.username,
        )
        print("Current user:", self.teacher_user.username)
        print("User in teacher group:", is_in_group(self.teacher_user, "teacher"))
        print(self.solution.assignment.deadline < timezone.now().date())
        print("Response status:", response.status_code)
        print("Response data:", response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.solution.refresh_from_db()
        self.assertEqual(self.solution.grade, 85.0)

        # Try as student — should fail
        self.client.force_login(self.student_user)
        response = self.client.post(grade_url, {"grade": 90})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try as manager — should fail
        self.client.force_login(self.manager_user)
        response = self.client.post(grade_url, {"grade": 95})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
