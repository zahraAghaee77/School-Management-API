from django.db import models

from schools.models import Class, School
from users.models import User


class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_news"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="news", null=True, blank=True
    )
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="news", null=True, blank=True
    )

    def __str__(self):
        return f"{self.title} - {self.content[:30]}"
