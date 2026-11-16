"""One Lesson is one occurrence, not a recurring template or a weekday rule."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .teaching_models import (  # noqa: F401 -- register domain models with Django's app registry.
    AcademicActivity,
    Assessment,
    AssessmentChange,
    TeachingAssignment,
)


class Lesson(models.Model):
    class Kind(models.TextChoices):
        LECTURE = "lecture", "Лекция"
        SEMINAR = "seminar", "Семинар"
        PRACTICE = "practice", "Практика"
        LAB = "lab", "Лабораторная"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "По расписанию"
        MOVED = "moved", "Перенесено"
        CANCELLED = "cancelled", "Отменено"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        "accounts.StudyGroup", on_delete=models.PROTECT, related_name="lessons"
    )
    subject = models.CharField(max_length=200)
    teacher = models.CharField(max_length=200)
    room = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.LECTURE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]
        indexes = [models.Index(fields=["group", "starts_at"], name="lesson_group_start_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="lesson_positive_duration",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="lesson_positive_revision"
            ),
        ]

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at:
            if timezone.is_naive(self.starts_at) or timezone.is_naive(self.ends_at):
                raise ValidationError("Время занятия должно содержать часовой пояс.")
            if self.ends_at <= self.starts_at:
                raise ValidationError({"ends_at": "Занятие должно закончиться позже начала."})

    def __str__(self):
        return f"{self.subject} — {self.group}"


class LessonChange(models.Model):
    """Committed changes are durable notification inputs for #9; deduplicate by id.

    No signals/background mail here. Consumers see this row only once the same
    transaction that changes the lesson commits. Do not edit/delete this history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name="changes")
    revision = models.PositiveIntegerField()
    reason = models.CharField(max_length=500)
    before = models.JSONField()
    after = models.JSONField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "revision"], name="lesson_change_unique_revision"
            )
        ]
