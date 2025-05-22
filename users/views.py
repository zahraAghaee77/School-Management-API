from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import *
from rest_framework.response import Response
from rest_framework.views import APIView

from schools.models import *
from schools.serializers import *

from .models import User
from .permissions import IsStudent, IsTeacher
from .serializers import RegisterSerializer, UpdateBioSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UpdateBioSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
    )
    def see(self, request):
        users = User.objects.all()
        serializer = ComplexUserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(operation_description="Activate user by admin.")
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsAdminUser],
    )
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response(
            {"message": "User activated successfully."},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(operation_description="See all lessons of teacher.")
    @action(
        detail=False,
        methods=["get"],
        url_name="teacher-lessons",
        url_path="teacher-lessons",
        permission_classes=[IsTeacher],
    )
    def teacher_lessons(self, request):
        try:
            lessons = Lesson.objects.filter(
                class_lessons__teacher=request.user
            ).distinct()
            serializer = LessonSerializer(lessons, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(operation_description="See all lessons of student.")
    @action(
        detail=False,
        methods=["get"],
        url_name="student-lessons",
        url_path="student-lessons",
        permission_classes=[IsStudent],
    )
    def student_lessons(self, request):
        try:
            lessons = Lesson.objects.filter(
                class_lessons__students=request.user
            ).distinct()
            serializer = LessonSerializer(lessons, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().list(request, *args, **kwargs)
        return Response(
            {"detail": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def create(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().create(request, *args, **kwargs)
        return Response(
            {"detail": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {"detail": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class UserRegistrationView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "data": serializer.data,
                    "message": "You registered successfully, please wait for admin approval.",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
