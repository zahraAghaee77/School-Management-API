from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from schools.models import Class, School

from .models import News
from .permissions import *
from .serializers import ManagerNewsSerializer, NewsSerializer, TeacherNewsSerializer


class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = News.objects.select_related("creator", "school", "class_obj")
        if user.groups.filter(name="manager").exists():
            school = user.school_manager
            return queryset.filter(
                Q(school=school) | Q(class_obj__school=school) | Q(creator=user)
            )

        elif user.groups.filter(name="teacher").exists():
            class_ids = user.class_teacher.values_list("id", flat=True)
            school_ids = user.class_teacher.values_list("school_id", flat=True)
            return News.objects.filter(
                Q(class_obj__in=class_ids) | Q(school_id__in=school_ids)
            )

        elif user.groups.filter(name="student").exists():
            class_ids = user.class_students.values_list("id", flat=True)
            school_ids = user.class_students.values_list("school_id", flat=True)
            return News.objects.filter(
                Q(class_obj__in=class_ids) | Q(school_id__in=school_ids)
            )

        return News.objects.none()

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AnyOf(IsTeacherOfClass, IsManagerOfSchool)]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsCreatorOrManager]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        if self.request.method == "POST":
            if self.request.data.get("school_id"):
                return ManagerNewsSerializer
            elif self.request.data.get("class_id"):
                return TeacherNewsSerializer
        return NewsSerializer

    def perform_create(self, serializer):
        user = self.request.user
        class_id = self.request.data.get("class_id")
        school_id = self.request.data.get("school_id")

        if class_id:
            class_obj = get_object_or_404(Class, id=class_id)
            if class_obj.teacher != user:
                raise PermissionDenied("You can only post news to your own class.")
            serializer.save(creator=user, class_obj=class_obj)

        elif school_id:
            school = get_object_or_404(School, id=school_id)
            if hasattr(user, "school_manager") and user.school_manager == school:
                serializer.save(creator=user, school=school)
            else:
                raise PermissionDenied("Only managers can post school-wide news.")

        else:
            raise PermissionDenied("You must specify either a class or a school.")
