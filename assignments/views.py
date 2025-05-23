from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schools.models import Lesson
from users.models import User

from .models import Assignment, Solution
from .permissions import *
from .serializers import *


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all().order_by("created_at")
    serializer_class = AssignmentSerializer

    def get_permissions(self):
        if self.action in ["retrieve", "list"]:
            permission_classes = [CanViewAssignment]
        elif self.action == "create":
            permission_classes = [IsTeacherOfLesson]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [CanUpdateAssignment]
        elif self.action == "add_answer":
            permission_classes = [CanAddAnswer]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        user = self.request.user

        if is_in_group(user, "teacher"):
            return Assignment.objects.filter(class_obj__teacher=user).order_by(
                "created_at"
            )
        elif is_in_group(user, "student"):
            return Assignment.objects.filter(class_obj__students=user).order_by(
                "created_at"
            )
        elif is_in_group(user, "manager"):
            if hasattr(user, "school_manager"):
                school = user.school_manager
                return Assignment.objects.filter(class_obj__school=school)
        if user.is_staff:
            return Assignment.objects.all()

        return Assignment.objects.none()

    def get_serializer_class(self):
        if self.action in ["update", "partial_update", "create"]:
            return CreateAssignmentSerializer
        elif self.action == "add_answer":
            return AssignmentsSolutionSerializer
        return super().get_serializer_class()

    @swagger_auto_schema(
        operation_summary="Create a new assignment",
        operation_description="Teachers can create an assignment for a specific class and lesson.",
        request_body=CreateAssignmentSerializer,
        responses={201: AssignmentSerializer()},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="List all assignments",
        operation_description="Students see assignments from their classes. Teachers see assignments they created.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Add or update the answer after deadline",
        operation_description="Only the teacher who created the assignment can add/update the answer.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "answer_text": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Answer text (optional if file provided)",
                ),
                "answer_file": openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Answer file (PDF or ZIP)",
                    format="binary",
                ),
            },
            required=[],
            description="Provide either answer text or answer file",
        ),
        responses={
            200: AssignmentSerializer,
            404: openapi.Response(description="Assignment not found"),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="add-answer",
        url_name="add-answer",
        permission_classes=[CanAddAnswer],
        serializer_class=AssignmentsSolutionSerializer,
    )
    def add_answer(self, request, pk=None):
        """
        URL: /assignments/{assignment_id}/add-answer/
        Request Body: {"answer_text": "Sample text"} or {"answer_file": <file>}
        """
        try:
            assignment = self.get_object()
            answer_text = request.data.get("answer_text")
            answer_file = request.data.get("answer_file")

            if answer_text:
                assignment.answer_text = answer_text
            if answer_file:
                assignment.answer_file = answer_file

            assignment.save()
            serializer = self.get_serializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Assignment.DoesNotExist:
            return Response(
                {"detail": "The assignment was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class SolutionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Solution.objects.all()
    serializer_class = SolutionSerializer

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CreateSolutionSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user

        if is_in_group(user, "teacher"):
            assignment_id = self.kwargs.get("assignment_id")
            if assignment_id:
                return Solution.objects.filter(
                    assignment__id=assignment_id, assignment__class_obj__teacher=user
                )
            return Solution.objects.filter(assignment__class_obj__teacher=user)

        elif is_in_group(user, "student"):
            return Solution.objects.filter(student=user)
        elif is_in_group(user, "manager") and hasattr(user, "school_manager"):
            school = user.school_manager
            return Solution.objects.filter(assignment__class_obj__school=school)

        return Solution.objects.none()

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [IsStudentOfAssignment]
        elif self.action in ["update", "partial_update"]:
            permission_classes = [CanUpdateOwnSolution]
        elif self.action == "grade":
            permission_classes = [CanGradeSolution]
        else:
            permission_classes = [CanViewSolution]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        user = self.request.user

        if not is_in_group(user, "student"):
            raise PermissionDenied("Only students can submit solutions.")

        assignment = serializer.validated_data.get("assignment")
        if not assignment:
            raise ValidationError({"assignment": "Assignment must be provided."})

        serializer.save(student=user, assignment=assignment)

    @swagger_auto_schema(
        operation_summary="Submit a solution to an assignment",
        operation_description="Students can submit text or file-based solutions before the deadline.",
        request_body=SolutionSerializer,
        responses={201: SolutionSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="List all solutions for an assignment by Teacher",
        operation_description="Teachers can view all student solutions for an assignment.",
        responses={200: SolutionSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="assignment-solutions",
        url_name="assignment-solutions",
    )
    def assignment_solutions(self, request, pk=None):
        """
        URL: /solutions/{assignment_id}/assignment-solutions
        """
        try:
            assignment = Assignment.objects.get(id=pk, class_obj__teacher=request.user)
            solutions = Solution.objects.filter(assignment=assignment)
            serializer = self.get_serializer(solutions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Assignment.DoesNotExist:
            return Response(
                {"detail": "The assignment was not found or you do not have access."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @swagger_auto_schema(
        operation_summary="Grade a student's solution",
        operation_description="Only teachers can grade solutions.",
        request_body=TeacherGradeSolutionSerializer,
        responses={200: TeacherGradeSolutionSerializer},
    )
    @action(detail=True, methods=["post"], permission_classes=[CanGradeSolution])
    def grade(self, request, pk=None):
        """
        URL: /solutions/{solution_id}/grade/
        Request Body: {"grade": 75}
        """
        try:
            solution = self.get_object()
            grade = request.data.get("grade")

            if grade is None:
                return Response(
                    {"detail": "The grade must be provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            solution.grade = grade
            solution.save()
            serializer = self.get_serializer(solution)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Solution.DoesNotExist:
            return Response({"detail": "The solution not found."}, status=404)
