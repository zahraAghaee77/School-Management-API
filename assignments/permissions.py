from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import Assignment, Lesson, Solution


def is_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return is_in_group(request.user, "teacher")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return is_in_group(request.user, "manager")


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return is_in_group(request.user, "student")


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return request.user.is_staff or is_in_group(request.user, "manager")
        return True


class IsStudentReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return False
        return True


class IsTeacherOfLesson(BasePermission):
    def has_permission(self, request, view):
        lesson_id = request.data.get("lesson_id")
        if not lesson_id:
            return False

        try:
            lesson = Lesson.objects.get(id=lesson_id)
            return lesson.class_lessons.first().teacher == request.user
        except Lesson.DoesNotExist:
            return False


class CanUpdateAssignment(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.lesson.class_lessons.first().teacher == request.user
            and obj.deadline > timezone.now().date()
        )


class CanAddAnswer(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.class_obj.teacher == request.user
            and obj.deadline < timezone.now().date()
        )


class CanSubmitOrUpdateSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.student == request.user
            and obj.assignment.deadline > timezone.now().date()
        )


class IsTeacherOfAssignment(BasePermission):
    def has_permission(self, request, view):
        assignment_id = view.kwargs.get("pk")
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            return assignment.class_obj.teacher == request.user
        except Assignment.DoesNotExist:
            return False


class CanGradeSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not obj.assignment or not obj.assignment.class_obj:
            return False
        is_teacher = obj.assignment.class_obj.teacher == request.user
        deadline_passed = obj.assignment.deadline < timezone.now().date()
        return is_teacher and deadline_passed


class CanViewSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_in_group(request.user, "teacher"):
            return obj.assignment.class_obj.teacher == request.user
        elif is_in_group(request.user, "student"):
            return obj.student == request.user
        return False


class CanViewAssignment(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.groups.filter(name="teacher").exists():
            return obj.class_obj.teacher == user

        elif user.groups.filter(name="student").exists():
            return obj.class_obj.students.filter(id=user.id).exists()

        elif user.groups.filter(name="manager").exists() and hasattr(
            user, "school_manager"
        ):
            return obj.class_obj.school == user.school_manager

        return False


class IsStudentOfAssignment(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not user.groups.filter(name="student").exists():
            return False

        assignment_id = view.kwargs.get("pk")
        if not assignment_id:
            return False

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            raise PermissionDenied("Assignment not found.")

        return assignment.class_obj.students.filter(id=user.id).exists()


class CanUpdateOwnSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.groups.filter(name="student").exists():
            return False
        if obj.student != user:
            return False
        return obj.assignment.class_obj.students.filter(id=user.id).exists()
