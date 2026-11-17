from datetime import datetime, time, timedelta

from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView

from accounts.access import require_student

from .models import Lesson, LessonChange
from .serializers import (
    SCHEDULE_MAX_DATE,
    SCHEDULE_MIN_DATE,
    LessonPeriodSerializer,
    LessonSerializer,
)


def student_lessons(user):
    student = require_student(user)
    # Identity/group always come from the current database assignment, never GET.
    return (
        Lesson.objects.filter(group_id=student.group_id)
        .select_related("group")
        .prefetch_related(
            Prefetch(
                "changes",
                queryset=LessonChange.objects.order_by("-revision")[:1],
                to_attr="latest_changes",
            )
        )
    )


class LessonListView(ListAPIView):
    serializer_class = LessonSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "from", OpenApiTypes.DATE, description="Первый день включительно, 2000–2100 годы"
            ),
            OpenApiParameter(
                "to", OpenApiTypes.DATE, description="Последний день включительно, 2000–2100 годы"
            ),
        ],
        description="Расписание своей группы; по умолчанию текущая неделя в часовом поясе вуза.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()
        queryset = student_lessons(self.request.user)
        params = LessonPeriodSerializer(
            data={
                f"{name}_date": self.request.query_params[name]
                for name in ("from", "to")
                if name in self.request.query_params
            }
        )
        params.is_valid(raise_exception=True)
        today = timezone.localdate(timezone=timezone.get_default_timezone())
        start = params.validated_data.get("from_date", today - timedelta(days=today.weekday()))
        try:
            end = params.validated_data.get("to_date") or start + timedelta(days=6)
        except OverflowError:
            raise ValidationError({"period": "Дата выходит за допустимый диапазон."}) from None
        if not SCHEDULE_MIN_DATE <= start <= end <= SCHEDULE_MAX_DATE:
            raise ValidationError(
                {"period": "Укажите даты по порядку в диапазоне 2000–2100 годов."}
            )
        if (end - start).days > 30:
            raise ValidationError({"period": "Укажите период от 1 до 31 дня."})
        zone = timezone.get_default_timezone()
        lower = datetime.combine(start, time.min, tzinfo=zone)
        upper = datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone)
        # Include cross-midnight lessons; exclude those ending exactly at the boundary.
        return queryset.filter(starts_at__lt=upper, ends_at__gt=lower)


class LessonDetailView(RetrieveAPIView):
    serializer_class = LessonSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Lesson.objects.none()
        return student_lessons(self.request.user)
