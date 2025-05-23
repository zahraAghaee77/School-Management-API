from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from schools.serializers import *
from users.serializers import *

from .models import News


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "last_modified",
            "creator",
            "school",
            "class_obj",
        ]


class ManagerNewsSerializer(serializers.ModelSerializer):
    school_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = News
        fields = [
            "title",
            "content",
            "created_at",
            "last_modified",
            "school",
            "school_id",
        ]
        read_only_fields = ["creator", "school"]

    def validate(self, data):
        school_id = data.pop("school_id", None)
        if not school_id:
            raise serializers.ValidationError("You must specify the school.")
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            raise serializers.ValidationError("School does not exist.")
        data["school"] = school
        return data


class TeacherNewsSerializer(serializers.ModelSerializer):
    class_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = News
        fields = [
            "title",
            "content",
            "created_at",
            "last_modified",
            "class_obj",
            "class_id",
        ]
        read_only_fields = ["creator", "class_obj"]

    def validate(self, data):
        class_id = data.pop("class_id", None)
        if not class_id:
            raise serializers.ValidationError("You must specify the class.")

        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            raise serializers.ValidationError("Class does not exist.")

        data["class_obj"] = class_obj
        return data
