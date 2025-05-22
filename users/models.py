from django.contrib.auth.models import AbstractUser, Group
from django.db import models

from .managers import *

# Group.objects.get_or_create(name="teacher")
# Group.objects.get_or_create(name="student")
# Group.objects.get_or_create(name="manager")
# Group.objects.get_or_create(name="admin")


class User(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    national_id = models.CharField(
        unique=True,
        null=False,
        max_length=10,
        help_text="10-digit national id",
    )
    objects = UserManager()

    def __str__(self):
        return f"{self.username} - {self.bio}"

    def has_role(self, role_name):
        return self.groups.filter(name=role_name).exists()
