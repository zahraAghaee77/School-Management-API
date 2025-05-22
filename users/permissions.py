from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_role("teacher")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_role("manager")


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_role("student")


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_role("admin")
