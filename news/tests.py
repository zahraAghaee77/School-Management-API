from django.contrib.auth.models import Group, User
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from schools.models import Class, School
from users.models import User

from .models import News


class NewsAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create groups
        self.teacher_group, _ = Group.objects.get_or_create(name="Teacher")
        self.manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.student_group, _ = Group.objects.get_or_create(name="Student")

        # Create school
        self.school = School.objects.create(name="Test School")

        # Create manager user
        self.manager_user = User.objects.create_user(
            username="manager", password="testpass123"
        )
        self.manager_user.groups.add(self.manager_group)
        self.school.manager = self.manager_user
        self.school.save()

        # Create teacher user
        self.teacher_user = User.objects.create_user(
            username="teacher", password="testpass123"
        )
        self.teacher_user.groups.add(self.teacher_group)

        # Create student user
        self.student_user = User.objects.create_user(
            username="student", password="testpass123"
        )
        self.student_user.groups.add(self.student_group)

        # Create class with teacher
        self.classroom = Class.objects.create(
            name="Math 101", school=self.school, teacher=self.teacher_user
        )
        self.teacher_user.class_teacher.add(self.classroom)

        # Assign student to class
        self.student_user.class_students.add(self.classroom)

        # URLs
        self.news_url = "/news/news/"

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def test_teacher_can_create_class_news(self):
        self.authenticate_as(self.teacher_user)
        data = {
            "title": "Midterm Exam",
            "content": "Midterm next week!",
            "class_id": self.classroom.id,
        }
        response = self.client.post(self.news_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.first().creator, self.teacher_user)

    def test_non_class_teacher_cannot_create_news(self):
        other_teacher = User.objects.create_user(
            username="other_teacher", password="testpass123"
        )
        other_teacher.groups.add(self.teacher_group)
        self.authenticate_as(other_teacher)

        data = {
            "title": "Invalid News",
            "content": "Should not be allowed.",
            "class_id": self.classroom.id,
        }

        response = self.client.post(self.news_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_update_delete_own_news(self):
        news = News.objects.create(
            title="Old Title",
            content="Old Content",
            creator=self.teacher_user,
            class_obj=self.classroom,
        )

        self.authenticate_as(self.teacher_user)

        # Update
        update_data = {"title": "Updated Title", "content": "Updated Content"}
        response = self.client.patch(f"{self.news_url}{news.id}/", update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        news.refresh_from_db()
        self.assertEqual(news.title, "Updated Title")

        # Delete
        response = self.client.delete(f"{self.news_url}{news.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(News.objects.count(), 0)

    def test_teacher_cannot_edit_other_teachers_news(self):
        other_teacher = User.objects.create_user(
            username="other_teacher", password="testpass123"
        )
        other_teacher.groups.add(self.teacher_group)

        other_class = Class.objects.create(
            name="Other Class", school=self.school, teacher=other_teacher
        )
        other_news = News.objects.create(
            title="Other News",
            content="This is someone else's news.",
            creator=other_teacher,
            class_obj=other_class,
        )

        self.authenticate_as(self.teacher_user)

        response = self.client.patch(
            f"{self.news_url}{other_news.id}/", {"title": "Hacked"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_school_news(self):
        self.authenticate_as(self.manager_user)
        data = {
            "title": "School Closure",
            "content": "School closed tomorrow.",
            "school_id": self.school.id,
        }
        response = self.client.post(self.news_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(News.objects.filter(school=self.school).count(), 1)

    def test_manager_can_manage_all_news_in_school(self):
        class_news = News.objects.create(
            title="Class News",
            content="From teacher",
            creator=self.teacher_user,
            class_obj=self.classroom,
        )
        school_news = News.objects.create(
            title="School News",
            content="From manager",
            creator=self.manager_user,
            school=self.school,
        )

        self.authenticate_as(self.manager_user)

        # GET all
        response = self.client.get(self.news_url)
        self.assertEqual(len(response.data), 2)

        # PATCH class news
        response = self.client.patch(
            f"{self.news_url}{class_news.id}/", {"content": "Updated by manager"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DELETE school news
        response = self.client.delete(f"{self.news_url}{school_news.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_student_can_see_but_not_modify_news(self):
        class_news = News.objects.create(
            title="Class News",
            content="FromClass",
            creator=self.teacher_user,
            class_obj=self.classroom,
        )
        school_news = News.objects.create(
            title="School News",
            content="FromSchool",
            creator=self.manager_user,
            school=self.school,
        )

        self.authenticate_as(self.student_user)

        # GET list
        response = self.client.get(self.news_url)
        self.assertEqual(len(response.data), 2)

        # GET detail
        response = self.client.get(f"{self.news_url}{class_news.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # PATCH
        response = self.client.patch(
            f"{self.news_url}{class_news.id}/", {"title": "Hacked"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # DELETE
        response = self.client.delete(f"{self.news_url}{class_news.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_access_to_news_by_id_fails(self):
        other_school = School.objects.create(name="Other School")
        other_manager = User.objects.create_user(
            username="other_manager", password="testpass123"
        )
        other_manager.groups.add(self.manager_group)
        other_school.manager = other_manager
        other_school.save()

        other_news = News.objects.create(
            title="Other School News",
            content="Private",
            creator=other_manager,
            school=other_school,
        )

        self.authenticate_as(self.manager_user)
        response = self.client.get(f"{self.news_url}{other_news.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
