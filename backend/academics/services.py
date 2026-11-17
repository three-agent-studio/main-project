"""All edits to existing lessons go here, including edits from Django Admin."""

from datetime import timezone

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Lesson, LessonChange

EDITABLE_FIELDS = frozenset(
    {"subject", "teacher", "room", "kind", "starts_at", "ends_at", "status"}
)


def snapshot(lesson):
    return {
        "group_id": lesson.group_id,
        **{
            name: getattr(lesson, name).astimezone(timezone.utc).isoformat()
            if name in {"starts_at", "ends_at"}
            else getattr(lesson, name)
            for name in sorted(EDITABLE_FIELDS)
        },
    }


@transaction.atomic
def change_lesson(lesson_id, *, changes, reason, actor=None, expected_revision=None):
    # Row locks serialize revisions on PostgreSQL. The optional revision also
    # prevents a stale admin form from silently overwriting another person's edit.
    lesson = Lesson.objects.select_for_update().get(pk=lesson_id)
    if expected_revision is not None and lesson.revision != expected_revision:
        raise ValidationError("Занятие уже изменилось. Обновите страницу и повторите действие.")
    if changes.keys() - EDITABLE_FIELDS:
        raise ValidationError("Нельзя менять группу, идентификатор или служебные поля занятия.")
    before = snapshot(lesson)
    for name, value in changes.items():
        setattr(lesson, name, value)
    if lesson.status != Lesson.Status.CANCELLED and any(
        before[name] != snapshot(lesson)[name] for name in ("starts_at", "ends_at", "room")
    ):
        lesson.status = Lesson.Status.MOVED
    lesson.full_clean()
    after = snapshot(lesson)
    if before == after:
        return lesson  # Repeated saves are not new events and do not bump revision.
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValidationError("Укажите причину изменения (от 1 до 500 символов).")
    lesson.revision += 1
    lesson.save()
    LessonChange.objects.create(
        lesson=lesson,
        revision=lesson.revision,
        reason=reason.strip(),
        before=before,
        after=after,
        changed_by=actor,
    )
    return lesson
