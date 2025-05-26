from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, fromstr
from django.contrib.gis.measure import D
from django.db import connection
from django.views import generic
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from users.models import User
from users.serializers import UserSerializer

from .models import *
from .permissions import *
from .serializers import *

"""
{
  "name": "Green Valley School",
  "location": {
    "type": "Point",
    "coordinates": [ -73.994454, 40.750042 ]
  },
  "manager": 1
}
"""


def get_nearby_school(lan, lat, radius):
    point = Point(lan, lat, srid=4326)
    radius = radius * 1000

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, manager_id,
                   ST_AsGeoJSON(location) as geojson,
                   ST_Distance(location::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS distance
            FROM schools_school
            WHERE ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
            ORDER BY distance ASC
        """,
            [lan, lat, lan, lat, radius],
        )
        nearbyes = cursor.fetchall()

    sorted_schools = []
    for row in nearbyes:
        school = {
            "id": row[0],
            "name": row[1],
            "manager": row[2],
            "geometry": row[3],
            "distance_km": round(row[4] / 1000, 2),
        }
        sorted_schools.append(school)

    return sorted_schools


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return School.objects.all()
        if in_group(user, "manager"):
            return School.objects.filter(manager=user)
        return School.objects.none()

    def perform_create(self, serializer):
        manager = serializer.validated_data.get("manager")
        if manager and hasattr(manager, "school_manager"):
            raise ValidationError(
                {"manager": "This user is already a manager of another school."}
            )
        serializer.save()

    @swagger_auto_schema(
        operation_summary="List all schools",
        operation_description="Returns a list of all schools in the system. "
        "Managers see only their school; staff sees all.",
        responses={200: SchoolSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific school",
        operation_description="Returns details about a specific school by ID.",
        responses={200: SchoolSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new school",
        operation_description="Only admins can create schools. "
        "Provide name, location (GeoJSON), and optional manager.",
        request_body=SchoolSerializer,
        responses={201: SchoolSerializer, 400: "Validation Error"},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update an existing school",
        operation_description="Only admins can update school information.",
        request_body=SchoolSerializer,
        responses={200: SchoolSerializer, 400: "Validation Error", 404: "Not Found"},
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially update a school",
        operation_description="Only admins can make partial updates to a school.",
        request_body=SchoolSerializer,
        responses={200: SchoolSerializer, 400: "Validation Error", 404: "Not Found"},
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a school",
        operation_description="Only admins can delete schools.",
        responses={204: "Successfully deleted", 404: "Not Found"},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get all students in this school.",
        operation_description="Returns a list of all students enrolled in any class of the school.",
        responses={200: UserSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsManagerOfSchool],
    )
    def students(self, request, pk=None):
        try:
            school = self.get_object()
            students = (
                User.objects.filter(
                    class_students__school=school,
                )
                .filter(groups__name="student")
                .distinct()
            )
            serializer = UserSerializer(students, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except School.DoesNotExist:
            return Response(
                {"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Get all classes in this school.",
        operation_description="Returns a list of all classes taught in this school.",
        responses={200: ClassSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsManagerOfSchool])
    def classes(self, request, pk=None):
        try:
            school = self.get_object()
            classes = Class.objects.filter(school=school)
            serializer = ClassSerializer(classes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except School.DoesNotExist:
            return Response(
                {"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Get all lessons taught in this school.",
        operation_description="Returns a list of all lessons taught in any class of this school.",
        responses={200: LessonSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsManagerOfSchool],
    )
    def lessons(self, request, pk=None):
        try:
            school = self.get_object()
            lessons = Lesson.objects.filter(class_lessons__school=school).distinct()
            serializer = LessonSerializer(lessons, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except School.DoesNotExist:
            return Response(
                {"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Get all teachers in this school.",
        operation_description="Returns a list of all teachers teaching in this school.",
        responses={200: UserSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], permission_classes=[IsManagerOfSchool])
    def teachers(self, request, pk=None):
        try:
            school = self.get_object()
            teachers = (
                User.objects.filter(
                    class_teacher__school=school,
                )
                .filter(groups__name="teacher")
                .distinct()
            )
            serializer = UserSerializer(teachers, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except School.DoesNotExist:
            return Response(
                {"detail": "School not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="nearby1",
        permission_classes=[IsAuthenticated],
    )
    def nearby1(self, request):
        try:
            lat = float(request.data.get("lat"))
            lng = float(request.data.get("lng"))
            user_location = Point(lng, lat, srid=4326)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid or missing 'lat'/'lng' in request body."}, status=400
            )

        radius_km = float(request.data.get("radius", 10))
        print(radius_km)
        nearby_schools = (
            School.objects.annotate(distance=Distance("location", user_location))
            .filter(location__distance_lte=(user_location, D(km=radius_km)))
            .order_by("distance")
        )
        print("nearby_schools count:", nearby_schools.count())
        serializer = self.get_serializer(nearby_schools, many=True)
        features = serializer.data["features"]
        response_data = []

        for school_obj, feature in zip(nearby_schools, features):
            feature["properties"]["distance_km"] = round(school_obj.distance.km, 2)
            response_data.append(feature)

        return Response({"type": "FeatureCollection", "features": response_data})

    @action(
        detail=False,
        methods=["post"],
        url_path="nearby",
        permission_classes=[IsAuthenticated],
    )
    def nearby(self, request):
        try:
            lat = float(request.data.get("lat"))
            lng = float(request.data.get("lng"))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid or missing 'lat'/'lng' in request body."}, status=400
            )

        radius_km = float(request.data.get("radius", 10))
        sorted_schools = get_nearby_school(lan=lng, lat=lat, radius=radius_km)
        return Response(sorted_schools)


@swagger_auto_schema(
    tags=["Class Management"],
    operation_description="Manage class data, including adding/removing students and lessons.",
)
class ClassViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSerializer
    queryset = Class.objects.all()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CreateClassSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Class.objects.all().order_by("school")
        if in_group(user, "teacher"):
            return Class.objects.filter(teacher=user)
        if in_group(user, "student"):
            return Class.objects.filter(students=user)
        if in_group(user, "manager"):
            return Class.objects.filter(school__manager=user)
        return Class.objects.none()

    @swagger_auto_schema(
        operation_summary="Create a new class",
        operation_description="Only staff users can create classes.",
        request_body=CreateClassSerializer,
        responses={201: ClassSerializer},
    )
    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to create classes.")
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update an existing class",
        operation_description="Only staff users can update classes.",
        request_body=CreateClassSerializer,
        responses={200: ClassSerializer},
    )
    def update(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to update classes.")
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a class",
        operation_description="Only staff users can delete classes.",
        responses={204: "No content"},
    )
    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to delete classes.")
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add student to a class",
        operation_description="Only the teacher of the class can perform this action.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "national_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="National ID of the student"
                )
            },
            required=["national_id"],
        ),
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    example={"detail": "The student was added successfully."},
                ),
            ),
            400: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
            404: openapi.Response(
                description="Student or class not found",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="add-student",
        url_name="add-student",
        permission_classes=[IsTeacherOfClass],
    )
    def add_student(self, request, pk=None):
        try:
            class_obj = self.get_object()
            national_id = request.data.get("national_id")
            if not national_id:
                return Response(
                    {"detail": "The national id is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                student = User.objects.get(
                    national_id=national_id, groups__name="student"
                )
            except User.DoesNotExist:
                return Response(
                    {
                        "detail": f"The student with national_id = {national_id} does not exist or is not a student."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if class_obj.students.filter(id=student.id).exists():
                return Response(
                    {"detail": "The student is already in this class."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            class_obj.students.add(student)
            return Response(
                {"detail": "The student was added successfully."},
                status=status.HTTP_200_OK,
            )
        except Class.DoesNotExist:
            return Response(
                {"detail": "Class not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Remove student from a class",
        operation_description="Only the class teacher can remove students.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "national_id": openapi.Schema(
                    type=openapi.TYPE_STRING, description="National ID of the student"
                )
            },
            required=["national_id"],
        ),
        responses={
            200: openapi.Response(
                description="Success", schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            400: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
            404: openapi.Response(
                description="Student or class not found",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="remove-student",
        url_name="remove-student",
        permission_classes=[IsTeacherOfClass],
    )
    def remove_student(self, request, pk=None):
        try:
            class_obj = self.get_object()
            national_id = request.data.get("national_id")
            if not national_id:
                return Response(
                    {"detail": "The national id is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                student = User.objects.get(
                    national_id=national_id, groups__name="student"
                )
            except User.DoesNotExist:
                return Response(
                    {
                        "detail": f"The student with national_id = {national_id} does not exist or is not a student."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not class_obj.students.filter(id=student.id).exists():
                return Response(
                    {"detail": "The student was not in this class."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            class_obj.students.remove(student)
            return Response(
                {"detail": "The student was removed from class successfully."},
                status=status.HTTP_200_OK,
            )
        except Class.DoesNotExist:
            return Response(
                {"detail": "Class not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="List all students in a class",
        operation_description="Only the class teacher can see the list of students.",
        responses={200: UserSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsTeacherOfClass],
    )
    def students(self, request, pk=None):
        try:
            class_obj = self.get_object()
            students_class = class_obj.students.all()
            serializer = UserSerializer(students_class, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Class not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Add lesson to a class",
        operation_description="Only managers of the class's school can add lessons.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Name of the lesson"
                )
            },
            required=["name"],
        ),
        responses={
            200: openapi.Schema(type=openapi.TYPE_OBJECT),
            400: openapi.Schema(type=openapi.TYPE_OBJECT),
            404: openapi.Schema(type=openapi.TYPE_OBJECT),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="add-lesson",
        url_name="add-lesson",
        permission_classes=[IsManagerOfClass],
    )
    def add_lesson(self, request, pk=None):
        try:
            class_obj = self.get_object()
            lesson_name = request.data.get("name")
            if not lesson_name:
                return Response(
                    {"detail": "The lesson name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            lesson, created = Lesson.objects.get_or_create(name=lesson_name)

            if class_obj.lessons.filter(id=lesson.id).exists():
                return Response(
                    {"detail": "This lesson is already added."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            class_obj.lessons.add(lesson)
            return Response(
                {"detail": "Lesson added successfully."}, status=status.HTTP_200_OK
            )
        except Class.DoesNotExist:
            return Response(
                {"detail": "Class not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="List all lessons in a class",
        operation_description="Accessible by teachers, students, or managers of the class.",
        responses={200: LessonSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsTeacherOfClass | IsStudentOfClass | IsManagerOfClass],
    )
    def lessons(self, request, pk=None):
        try:
            class_obj = self.get_object()
            lessons = class_obj.lessons.all()
            serializer = LessonSerializer(lessons, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Class.DoesNotExist:
            return Response(
                {"detail": "Class not found."}, status=status.HTTP_404_NOT_FOUND
            )
