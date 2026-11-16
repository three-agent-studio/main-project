from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Lesson, LessonChange


class LessonChangeSerializer(serializers.ModelSerializer):
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
