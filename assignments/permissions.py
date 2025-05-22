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
            and obj.deadline > timezone.now()
        )


class CanAddAnswer(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.class_obj.teacher == request.user and obj.deadline < timezone.now()


class CanSubmitOrUpdateSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.student == request.user and obj.assignment.deadline > timezone.now()


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
        return (
            obj.assignment.class_obj.teacher == request.user
            and obj.assignment.deadline < timezone.now()
        )


class CanViewSolution(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_in_group(request.user, "teacher"):
            return obj.assignment.class_obj.teacher == request.user
        elif is_in_group(request.user, "student"):
            return obj.student == request.user
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
    """
    Allows students (based on group) to update their own solution,
    only if the assignment is for a class they belong to.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Must be in the 'student' group
        if not user.groups.filter(name="student").exists():
            return False

        # Must be their own solution
        if obj.student != user:
            return False

        # Must belong to a class the student is in
        return obj.assignment.class_obj.students.filter(id=user.id).exists()
