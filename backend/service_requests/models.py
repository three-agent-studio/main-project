import uuid

from django.conf import settings
from django.db import models


class ServiceRequest(models.Model):
    class Kind(models.TextChoices):
        CERTIFICATE = "certificate", "Справка об обучении"
        APPLICATION = "application", "Заявление в деканат"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Подана"
        IN_PROGRESS = "in_progress", "В работе"
        READY = "ready", "Готова"
        REJECTED = "rejected", "Отклонена"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey("accounts.StudentProfile", on_delete=models.PROTECT)
    request_key = models.UUIDField(editable=False)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    text = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    revision = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "request_key"], name="service_request_retry_key"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["submitted", "in_progress", "ready", "rejected"]),
                name="service_request_known_status",
            ),
        ]


class RequestEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(ServiceRequest, on_delete=models.PROTECT, related_name="history")
    status = models.CharField(max_length=20, choices=ServiceRequest.Status.choices)
    revision = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "revision"], name="service_request_event_revision"
            )
        ]
