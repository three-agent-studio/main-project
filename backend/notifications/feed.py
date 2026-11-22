from datetime import timedelta

from django.db.models import Case, CharField, Exists, F, OuterRef, Q, Value, When
from django.db.models.functions import Cast, Concat
from django.utils import timezone

from academics.models import AcademicActivity, LessonChange
from service_requests.models import RequestEvent, ServiceRequest

from .models import Announcement, NoticeRead

COLUMNS = ("key", "category", "headline", "body", "occurred_at", "read")


def rows(source, student, key=None):
    now = timezone.now()
    # Build all sources from the *current* profile. A receipt is never an access grant.
    sources = {
        "news": (
            Announcement.objects.filter(published_at__lte=now).filter(
                Q(faculty=None) | Q(faculty_id=student.group.faculty_id)
            ),
            "title",
            F("message"),
            "published_at",
        ),
        "schedule": (
            LessonChange.objects.filter(
                lesson__group_id=student.group_id, lesson__ends_at__gte=now
            ),
            "lesson__subject",
            F("reason"),
            "created_at",
        ),
        "request": (
            RequestEvent.objects.filter(ticket__student=student).exclude(
                status=ServiceRequest.Status.SUBMITTED
            ),
            "ticket__kind",
            F("comment"),
            "created_at",
        ),
        "deadline": (
            AcademicActivity.objects.filter(
                assignment__group_id=student.group_id,
                is_cancelled=False,
                due_at__gt=now,
                due_at__lte=now + timedelta(hours=48),
            ),
            "title",
            Value("Срок сдачи в ближайшие 48 часов."),
            "due_at",
        ),
    }
    qs, title, body, at = sources[source]
    if source == "request":
        headline = Concat(
            Case(
                *(
                    When(ticket__kind=v, then=Value(label))
                    for v, label in ServiceRequest.Kind.choices
                )
            ),
            Value(" · "),
            Case(
                *(When(status=v, then=Value(label)) for v, label in ServiceRequest.Status.choices)
            ),
        )
    else:
        headline = F(title)
    parts = [Value(source + "-"), Cast("pk", CharField())]
    if source == "deadline":
        # A changed due time gets a new receipt; refreshing never duplicates a reminder.
        parts += [Value("-"), Cast("due_at", CharField())]
    qs = qs.order_by().annotate(
        key=Concat(*parts),
        category=Value(source),
        headline=headline,
        body=body,
        occurred_at=F(at),
    )
    if key is not None:
        qs = qs.filter(key=key)
    return qs.annotate(
        read=Exists(
            NoticeRead.objects.filter(
                user_id=student.user_id,
                key=OuterRef("key"),
            )
        )
    ).values(*COLUMNS)


def feed(student):
    return (
        rows("news", student)
        .union(
            *(rows(source, student) for source in ("schedule", "request", "deadline")),
            all=True,
        )
        .order_by("-occurred_at", "key")
    )
