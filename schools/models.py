from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.db import models

from users.models import User


class School(models.Model):
    name = models.CharField(max_length=255)
    location = gis_models.PointField(srid=4326)
    manager = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name="school_manager",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Lesson(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Class(models.Model):
    name = models.CharField(max_length=255)

    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="class_teacher",
        null=True,
        blank=True,
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classes")
    students = models.ManyToManyField(User, related_name="class_students", blank=True)
    lessons = models.ManyToManyField(Lesson, related_name="class_lessons", blank=True)

    def __str__(self):
        teacher_name = self.teacher.get_full_name() if self.teacher else "No teacher"
        return f"{self.name} - {self.school.name} - {teacher_name}"
