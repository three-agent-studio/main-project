from django.core.exceptions import ValidationError as ModelValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.models import StudentProfile

from .models import AcademicActivity, Assessment, TeachingAssignment
from .teaching_access import teacher_assignments


def validate_model(instance):
    try:
        instance.full_clean()
    except ModelValidationError as exc:
        raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages)) from None


class AssignmentSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = ["id", "group", "group_name", "subject", "term"]
        read_only_fields = fields


class ActivityPublicSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source="assignment.subject", read_only=True)
    term = serializers.CharField(source="assignment.term", read_only=True)
    group_name = serializers.CharField(source="assignment.group.name", read_only=True)
    teacher = serializers.CharField(source="assignment.teacher.full_name", read_only=True)

    class Meta:
        model = AcademicActivity
        fields = [
            "id",
            "assignment",
            "subject",
            "term",
            "group_name",
            "teacher",
            "kind",
            "title",
            "description",
            "scheduled_at",
            "due_at",
            "room",
            "is_cancelled",
            "revision",
            "updated_at",
        ]
        read_only_fields = fields


class ActivityWriteSerializer(ActivityPublicSerializer):
    assignment = serializers.PrimaryKeyRelatedField(queryset=TeachingAssignment.objects.none())
    expected_revision = serializers.IntegerField(min_value=1, required=False, write_only=True)

    class Meta(ActivityPublicSerializer.Meta):
        fields = [*ActivityPublicSerializer.Meta.fields, "expected_revision"]
        read_only_fields = ["id", "revision", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request:
            self.fields["assignment"].queryset = teacher_assignments(request.user)

    def validate(self, attrs):
        if self.instance:
            if attrs.get("assignment", self.instance.assignment) != self.instance.assignment:
                raise serializers.ValidationError({"assignment": "Назначение менять нельзя."})
            if attrs.get("kind", self.instance.kind) != self.instance.kind:
                raise serializers.ValidationError({"kind": "Вид работы менять нельзя."})
            if attrs.get("expected_revision") != self.instance.revision:
                raise serializers.ValidationError(
                    {"expected_revision": "Данные изменились. Обновите страницу."}
                )
        return attrs

    def create(self, validated_data):
        validated_data.pop("expected_revision", None)
        instance = AcademicActivity(**validated_data)
        validate_model(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("expected_revision", None)
        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.revision += 1
        validate_model(instance)
        instance.save()
        return instance


class AssessmentSerializer(serializers.ModelSerializer):
    activity = ActivityPublicSerializer(read_only=True)
    student = serializers.IntegerField(source="student_id", read_only=True)
    is_debt = serializers.SerializerMethodField()

    def get_is_debt(self, obj) -> bool:
        return obj.status in {Assessment.Status.DEBT, Assessment.Status.FAILED} or obj.score == 2

    class Meta:
        model = Assessment
        fields = [
            "id",
            "student",
            "activity",
            "status",
            "score",
            "comment",
            "revision",
            "updated_at",
            "is_debt",
        ]
        read_only_fields = fields


class ResultInputSerializer(serializers.Serializer):
    student = serializers.IntegerField(min_value=1)
    expected_revision = serializers.IntegerField(min_value=0, default=0)
    status = serializers.ChoiceField(choices=Assessment.Status.choices)
    score = serializers.IntegerField(min_value=2, max_value=5, allow_null=True, default=None)
    comment = serializers.CharField(max_length=2000, allow_blank=True, default="")

    def validate(self, attrs):
        graded = attrs["status"] == Assessment.Status.GRADED
        if graded != (attrs["score"] is not None):
            raise serializers.ValidationError(
                {"score": "Оценка 2–5 указывается только для статуса «Оценка»."}
            )
        return attrs


class RosterSerializer(serializers.ModelSerializer):
    result = serializers.SerializerMethodField()

    @extend_schema_field(AssessmentSerializer(allow_null=True))
    def get_result(self, obj):
        return AssessmentSerializer(obj.grade_results[0]).data if obj.grade_results else None

    class Meta:
        model = StudentProfile
        fields = ["id", "full_name", "result"]
        read_only_fields = fields
