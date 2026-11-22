import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    faculty = models.ForeignKey("accounts.Faculty", null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=180)
    message = models.TextField(max_length=1500)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return self.title


class NoticeRead(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], name="notification_unique_read")
        ]
