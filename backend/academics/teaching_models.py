"""Teaching assignments are explicit grants, never inferred from a name or is_staff."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TeachingAssignment(models.Model):
    teacher = models.ForeignKey(
        "accounts.TeacherProfile", on_delete=models.PROTECT, related_name="assignments"
    )
    group = models.ForeignKey(
        "accounts.StudyGroup", on_delete=models.PROTECT, related_name="teaching_assignments"
    )
    subject = models.CharField(max_length=200)
    term = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subject", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "group", "subject", "term"], name="teaching_assignment_unique"
            )
        ]

    def clean(self):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and any(
                getattr(previous, field) != getattr(self, field)
                for field in ("teacher_id", "group_id", "subject", "term")
            ):
                raise ValidationError("Назначение неизменяемо: отключите его и создайте новое.")
        if self.teacher_id and self.group_id:
            if self.teacher.faculty_id != self.group.faculty_id:
                raise ValidationError(
                    "Группа и преподаватель должны относиться к одному факультету."
                )

    def __str__(self):
        return f"{self.subject} — {self.group} — {self.term}"


class AcademicActivity(models.Model):
    class Kind(models.TextChoices):
        HOMEWORK = "homework", "Домашнее задание"
        TEST = "test", "Контрольная"
        CREDIT = "credit", "Зачёт"
        EXAM = "exam", "Экзамен"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        TeachingAssignment, on_delete=models.PROTECT, related_name="activities"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5000, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    room = models.CharField(max_length=100, blank=True)
    is_cancelled = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="activity_positive_revision"
            )
        ]

    def clean(self):
        if self.kind == self.Kind.HOMEWORK and not self.due_at:
            raise ValidationError({"due_at": "Укажите срок сдачи домашнего задания."})
        if self.kind != self.Kind.HOMEWORK and not self.scheduled_at:
            raise ValidationError({"scheduled_at": "Укажите дату и время занятия."})
        if self.due_at and self.scheduled_at and self.due_at < self.scheduled_at:
            raise ValidationError({"due_at": "Срок сдачи не может быть раньше начала."})


class Assessment(models.Model):
    class Status(models.TextChoices):
        GRADED = "graded", "Оценка"
        PASSED = "passed", "Зачтено"
        FAILED = "failed", "Не зачтено"
        DEBT = "debt", "Задолженность"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(AcademicActivity, on_delete=models.PROTECT, related_name="results")
    student = models.ForeignKey(
        "accounts.StudentProfile", on_delete=models.PROTECT, related_name="assessments"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(max_length=2000, blank=True)
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "student"], name="assessment_unique_student"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="graded", score__gte=2, score__lte=5, score__isnull=False)
                    | models.Q(status__in=["passed", "failed", "debt"], score__isnull=True)
                ),
                name="assessment_valid_result",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gte=1), name="assessment_positive_revision"
            ),
        ]


class AssessmentChange(models.Model):
    """Append-only result audit. A new grade never destroys the previous decision."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="changes")
    revision = models.PositiveIntegerField()
    before = models.JSONField(null=True)
    after = models.JSONField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "revision"], name="assessment_change_revision"
            )
        ]
