from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from accounts.models import StudentProfile

from .models import Assessment, AssessmentChange
from .teaching_access import teacher_activities
from .teaching_serializers import validate_model


def result_snapshot(result):
    return {name: getattr(result, name) for name in ("status", "score", "comment")}


@transaction.atomic
def set_result(user, activity_id, *, student, expected_revision, status, score, comment):
    # Locking the parent also serializes first-time inserts for the same activity.
    # Re-read the grant inside the write transaction, never trust a posted teacher id.
    activity = get_object_or_404(teacher_activities(user).select_for_update(), pk=activity_id)
    if activity.is_cancelled:
        raise ValidationError("Нельзя выставлять результат отменённой работы.")
    learner = get_object_or_404(
        StudentProfile.objects.select_for_update(),
        pk=student,
        group_id=activity.assignment.group_id,
    )
    result = Assessment.objects.filter(activity=activity, student=learner).first()
    if expected_revision != (result.revision if result else 0):
        raise ValidationError({"expected_revision": "Результат изменился. Обновите ведомость."})
    before = result_snapshot(result) if result else None
    if result is None:
        result = Assessment(activity=activity, student=learner)
    result.status, result.score, result.comment = status, score, comment
    after = result_snapshot(result)
    if before == after:
        return result, False
    created = before is None
    if not created:
        result.revision += 1
    validate_model(result)
    result.save()
    AssessmentChange.objects.create(
        assessment=result, revision=result.revision, before=before, after=after, actor=user
    )
    return result, created
