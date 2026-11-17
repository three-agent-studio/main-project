from datetime import date

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Lesson, LessonChange

SCHEDULE_MIN_DATE = date(2000, 1, 1)
SCHEDULE_MAX_DATE = date(2100, 12, 31)


class LessonChangeSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # The durable event retains its internal FK for notification consumers;
        # the student's DTO has no need for database identifiers in snapshots.
        for name in ("before", "after"):
            data[name] = {key: value for key, value in data[name].items() if key != "group_id"}
        return data

    class Meta:
        model = LessonChange
        fields = ["id", "revision", "reason", "before", "after", "created_at"]
        read_only_fields = fields


class LessonSerializer(serializers.ModelSerializer):
    group = serializers.CharField(source="group.name", read_only=True)
    last_change = serializers.SerializerMethodField()

    @extend_schema_field(LessonChangeSerializer(allow_null=True))
    def get_last_change(self, obj):
        return LessonChangeSerializer(obj.latest_changes[0]).data if obj.latest_changes else None

    class Meta:
        model = Lesson
        fields = [
            "id",
            "group",
            "subject",
            "teacher",
            "room",
            "kind",
            "starts_at",
            "ends_at",
            "status",
            "revision",
            "updated_at",
            "last_change",
        ]
        read_only_fields = fields


class LessonPeriodSerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs):
        for name, value in attrs.items():
            if not SCHEDULE_MIN_DATE <= value <= SCHEDULE_MAX_DATE:
                raise serializers.ValidationError(
                    {name: "Укажите дату в диапазоне 2000–2100 годов."}
                )
        return attrs
