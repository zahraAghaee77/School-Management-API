from django.urls import include, path

# urls.py
from rest_framework.routers import DefaultRouter

from assignments.views import AssignmentViewSet, SolutionViewSet

from .views import *

assignment_router = DefaultRouter()
assignment_router.register(r"assignments", AssignmentViewSet, basename="assignment")

solution_router = DefaultRouter()
solution_router.register(r"solutions", SolutionViewSet, basename="solution")

urlpatterns = [
    path("", include(assignment_router.urls)),
    path("", include(solution_router.urls)),
]
