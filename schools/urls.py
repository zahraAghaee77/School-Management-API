from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("schools", SchoolViewSet)
router.register("classes", ClassViewSet)
urlpatterns = [
    path("", include(router.urls)),
]
