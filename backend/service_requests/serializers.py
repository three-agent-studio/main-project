from pathlib import Path

from django.utils.text import get_valid_filename
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import RequestAttachment, RequestEvent, ServiceRequest

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
ATTACHMENT_FORMATS = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


class RequestAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestAttachment
        fields = ("filename", "size")
        read_only_fields = fields


class RequestEventSerializer(serializers.ModelSerializer):
    attachment = RequestAttachmentSerializer(read_only=True, allow_null=True)

    class Meta:
        model = RequestEvent
        fields = ("id", "status", "revision", "comment", "created_at", "attachment")
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


@extend_schema_field(OpenApiTypes.BINARY)
class AttachmentUploadField(serializers.FileField):
    pass


class TransitionWithAttachmentSerializer(TransitionSerializer):
    attachment = AttachmentUploadField(required=False, max_length=160)

    def validate_attachment(self, attachment):
        if attachment.size > MAX_ATTACHMENT_BYTES:
            raise serializers.ValidationError("Файл должен быть не больше 5 МБ.")
        signature = ATTACHMENT_FORMATS.get(Path(attachment.name).suffix.lower())
        if signature is None or attachment.read(len(signature)) != signature:
            raise serializers.ValidationError("Выберите действительный файл PDF, PNG или JPEG.")
        safe_name = get_valid_filename(attachment.name)
        if Path(safe_name).suffix.lower() not in ATTACHMENT_FORMATS:
            raise serializers.ValidationError("Добавьте имя файла перед расширением.")
        attachment.name = safe_name.lstrip(".")
        attachment.seek(0)
        return attachment
