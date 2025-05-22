from django.db import models

from schools.models import Class, Lesson
from users.models import User


class Assignment(models.Model):
    title = models.CharField(max_length=255)
    context = models.TextField(null=True, blank=True)
    grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=False, blank=True
    )  # max grade
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    attachment = models.FileField(upload_to="assignments/", null=True, blank=True)

    # Teacher-provided answer/solution
    answer_text = models.TextField(null=True, blank=True)
    answer_file = models.FileField(
        upload_to="assignments/answers/", null=True, blank=True
    )

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="assignments"
    )
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="assignments"
    )

    def __str__(self):
        return f"{self.title} - {self.class_obj.name}"


class Solution(models.Model):
    context = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    attachment = models.FileField(upload_to="solutions/", null=True, blank=True)

    grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )  # student grade

    student = models.ForeignKey(
        User, related_name="solutions", on_delete=models.CASCADE
    )
    assignment = models.ForeignKey(
        Assignment, related_name="solutions", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Solution by {self.student.username} for {self.assignment.title}"
