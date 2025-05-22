from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission

from .models import Class, School


class AnyOf(BasePermission):
    def __init__(self, *perms):
        self.perms = perms

    def has_permission(self, request, view):
        return any(p().has_permission(request, view) for p in self.perms)

    def has_object_permission(self, request, view, obj):
        return any(p().has_object_permission(request, view, obj) for p in self.perms)


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "teacher")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "manager")


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return user_in_group(request.user, "student")


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return request.user.is_staff or user_in_group(request.user, "manager")
        return True


class IsStudentReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return False
        return True


class IsMemberOfSchool(BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(request.user, "school_manager"):
            return obj.school == request.user.school_manager

        if user_in_group(request.user, "teacher"):
            return obj.school in [
                cls.school for cls in request.user.class_teacher.all()
            ]

        if user_in_group(request.user, "student"):
            return obj.school in [
                cls.school for cls in request.user.class_students.all()
            ]

        return False


class IsTeacherOfClass(BasePermission):
    def has_permission(self, request, view):
        class_id = request.data.get("class_id")
        if not class_id:
            return False

        try:
            class_obj = Class.objects.get(id=class_id)
            return request.user == class_obj.teacher
        except Class.DoesNotExist:
            return False


class IsManagerOfSchool(BasePermission):
    def has_permission(self, request, view):
        school_id = request.data.get("school_id")
        if not school_id:
            return False

        try:
            school = School.objects.get(id=school_id)
            return request.user == school.manager
        except School.DoesNotExist:
            return False


class CanViewNews(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.class_obj:
            if user_in_group(request.user, "student"):
                return obj.class_obj.students.filter(id=request.user.id).exists()
            elif user_in_group(request.user, "teacher"):
                return obj.class_obj.teacher == request.user
            elif user_in_group(request.user, "manager"):
                return obj.class_obj.school.manager == request.user
        elif obj.school:
            if user_in_group(request.user, "student"):
                return obj.school in [
                    cls.school for cls in request.user.class_students.all()
                ]
            elif user_in_group(request.user, "teacher"):
                return obj.school in [
                    cls.school for cls in request.user.class_teacher.all()
                ]
            elif user_in_group(request.user, "manager"):
                return obj.school.manager == request.user
        return False


class IsCreatorOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.creator == request.user:
            return True
        if (
            user_in_group(request.user, "manager")
            and obj.school == request.user.school_manager
        ):
            return True
        return False
