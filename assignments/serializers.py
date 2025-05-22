import os
from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from schools.models import Class, Lesson
from schools.serializers import ClassSerializer, LessonSerializer

from .models import Assignment, Solution


def validate_pdf_or_zip(value):
    extension = os.path.splitext(value.name)[1].lower()
    if extension not in [".pdf", ".zip"]:
        raise ValidationError("Only PDF or ZIP files are allowed.")
    return value


class AssignmentSerializer(serializers.ModelSerializer):
    class_obj = ClassSerializer(read_only=True)
    lesson = LessonSerializer(read_only=True)
    attachment = serializers.FileField(
        allow_empty_file=False, validators=[validate_pdf_or_zip], required=False
    )
    answer_file = serializers.FileField(
        allow_empty_file=False, validators=[validate_pdf_or_zip], required=False
    )

    class Meta:
        model = Assignment
        fields = [
            "id",
            "title",
            "context",
            "grade",
            "deadline",
            "attachment",
            "answer_text",
            "answer_file",
            "created_at",
            "last_modified",
            "class_obj",
            "lesson",
        ]
        read_only_fields = ["created_at", "last_modified", "class_obj", "lesson"]

    def validate(self, data):
        deadline = data.get("deadline")
        if isinstance(deadline, date) and deadline < timezone.now().date():
            raise ValidationError("Deadline must be in the future.")
        if data.get("grade", 0) > 100:
            raise ValidationError("Grade cannot exceed 100.")
        if not data.get("answer_text") and not data.get("answer_file"):
            raise ValidationError("Provide either answer text or an answer file.")
        return data


class CreateAssignmentSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(
        allow_empty_file=False,
        allow_null=True,
        required=False,
        validators=[validate_pdf_or_zip],
    )

    class Meta:
        model = Assignment
        fields = [
            "title",
            "context",
            "grade",
            "deadline",
            "attachment",
            "class_obj",
            "lesson",
        ]

    def validate(self, data):
        user = self.context["request"].user
        class_obj = data.get("class_obj")
        lesson = data.get("lesson")

        if not class_obj or not lesson:
            raise ValidationError("Both class and lesson must be provided.")

        if class_obj.teacher != user:
            raise ValidationError("You do not have permission for this class.")

        if lesson not in class_obj.lessons.all():
            raise ValidationError("The lesson does not belong to the class.")

        if data.get("grade", 0) > 100:
            raise ValidationError("Grade cannot exceed 100.")

        deadline = data.get("deadline")
        if isinstance(deadline, date) and deadline < timezone.now().date():
            raise ValidationError("Deadline must be in the future.")

        return data


class AssignmentsSolutionSerializer(serializers.ModelSerializer):
    answer_file = serializers.FileField(
        allow_empty_file=False, validators=[validate_pdf_or_zip], required=False
    )

    def validate(self, data):
        if not data.get("answer_text") and not data.get("answer_file"):
            raise ValidationError("Provide either answer text or an answer file.")
        return data

    class Meta:
        model = Assignment
        fields = [
            "answer_text",
            "answer_file",
        ]


class SolutionSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(
        allow_empty_file=False, required=False, validators=[validate_pdf_or_zip]
    )

    class Meta:
        model = Solution
        fields = [
            "id",
            "context",
            "attachment",
            "created_at",
            "last_modified",
            "grade",
            "student",
            "assignment",
        ]
        read_only_fields = ["created_at", "last_modified", "student", "grade"]

    def validate(self, data):
        assignment = data.get("assignment")
        if assignment.deadline < timezone.now():
            raise ValidationError("The assignment deadline has passed.")
        if not data.get("context") and not data.get("attachment"):
            raise ValidationError("Provide either solution text or a file.")
        return data


class TeacherGradeSolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solution
        fields = ["grade"]

    def validate_grade(self, value):
        if value > 100:
            raise ValidationError("Grade cannot exceed 100.")
        return value
