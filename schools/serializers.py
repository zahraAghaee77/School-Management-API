from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from users.models import *
from users.serializers import *

from .models import Class, Lesson, School


class SchoolSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name", "manager"]
        geo_field = "location"

    def validate_manager(self, value):
        if value and not value.groups.filter(name="manager").exists():
            raise ValidationError("The assigned user is not in the 'manager' group.")
        return value


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "name"]


class ClassSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    students = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Class
        fields = ["id", "name", "teacher", "school", "students", "lessons"]


class CreateClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = Class
        fields = ["name", "school", "teacher"]

    def validate(self, data):
        teacher = data.get("teacher")
        if teacher and not teacher.groups.filter(name="teacher").exists():
            raise ValidationError("The assigned user is not a teacher.")
        return data


"""

POST /schools/
Content-Type: application/json

{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [30.1234, 50.5678]
  },
  "properties": {
    "name": "My New School"
  }
}





"""
