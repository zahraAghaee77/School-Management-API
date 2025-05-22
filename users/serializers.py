from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "bio",
        ]


class ComplexUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_active"]


class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True)
    group = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "national_id",
            "username",
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "group",
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise ValidationError("Password does not match.")
        if len(data["national_id"]) != 10 or not data["national_id"].isdigit():
            raise ValidationError("Your national id must be 10 digits.")

        allowed_groups = ["student", "teacher", "manager"]
        if data["group"].lower() not in allowed_groups:
            raise ValidationError(
                f"Invalid group. Choose one of: {', '.join(allowed_groups)}"
            )

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        group_name = validated_data.pop("group").lower()

        user = User(**validated_data)
        user.is_active = False
        user.set_password(validated_data["password"])
        user.save()

        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        return user


class UpdateBioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("bio",)
