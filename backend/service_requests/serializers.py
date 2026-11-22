from rest_framework import serializers

from .models import RequestEvent, ServiceRequest


class RequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ("status", "revision", "comment", "created_at")
        read_only_fields = fields


class RequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    history = RequestEventSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            "id",
            "student_name",
            "kind",
            "text",
            "status",
            "revision",
            "created_at",
            "updated_at",
            "history",
        )
        read_only_fields = fields


class CreateRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ServiceRequest.Kind.choices)
    text = serializers.CharField(max_length=1000, allow_blank=True, default="")
    request_key = serializers.UUIDField()

    def validate(self, attrs):
        if attrs["kind"] == ServiceRequest.Kind.APPLICATION and not attrs["text"]:
            raise serializers.ValidationError({"text": "Опишите, с каким вопросом обращаетесь."})
        return attrs


class TransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ServiceRequest.Status.choices)
    expected_revision = serializers.IntegerField(min_value=1)
    comment = serializers.CharField(max_length=500, allow_blank=True, default="")
