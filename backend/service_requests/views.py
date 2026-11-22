from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from accounts.access import (
    IsDeaneryStaff,
    require_student,
    scope_faculty_records,
    scope_student_records,
)

from .models import RequestEvent, ServiceRequest
from .serializers import CreateRequestSerializer, RequestSerializer, TransitionSerializer


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"


def request_list():
    return ServiceRequest.objects.select_related("student").prefetch_related("history")


class StudentRequests(generics.ListCreateAPIView):
    serializer_class = RequestSerializer

    def get_queryset(self):
        return scope_student_records(request_list(), self.request.user)

    @extend_schema(
        request=CreateRequestSerializer, responses={201: RequestSerializer, 200: RequestSerializer}
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        student = require_student(request.user)
        incoming = CreateRequestSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        kind, text, key = (
            incoming.validated_data[field] for field in ("kind", "text", "request_key")
        )
        ticket, created = ServiceRequest.objects.get_or_create(
            student=student,
            request_key=key,
            defaults={"kind": kind, "text": text},
        )
        if created:
            RequestEvent.objects.create(
                ticket=ticket,
                status=ticket.status,
                revision=ticket.revision,
                actor=request.user,
            )
        elif (ticket.kind, ticket.text) != (kind, text):
            raise Conflict("Эта отправка уже сохранена. Создайте новую заявку для другого текста.")
        return Response(
            self.get_serializer(ticket).data, status=status.HTTP_201_CREATED if created else 200
        )


class StudentRequestDetail(generics.RetrieveAPIView):
    serializer_class = RequestSerializer

    def get_queryset(self):
        return scope_student_records(request_list(), self.request.user)


class StaffRequests(generics.ListAPIView):
    permission_classes = [IsDeaneryStaff]
    serializer_class = RequestSerializer

    def get_queryset(self):
        return scope_faculty_records(request_list(), self.request.user)


class StaffRequestDetail(generics.RetrieveAPIView):
    permission_classes = [IsDeaneryStaff]
    serializer_class = RequestSerializer

    def get_queryset(self):
        return scope_faculty_records(request_list(), self.request.user)


TRANSITIONS = {
    ServiceRequest.Status.SUBMITTED: {ServiceRequest.Status.IN_PROGRESS},
    ServiceRequest.Status.IN_PROGRESS: {
        ServiceRequest.Status.READY,
        ServiceRequest.Status.REJECTED,
    },
}


class StaffRequestStatus(generics.GenericAPIView):
    permission_classes = [IsDeaneryStaff]
    serializer_class = TransitionSerializer

    @extend_schema(responses={200: RequestSerializer})
    @transaction.atomic
    def post(self, request, pk):
        # Scope the lookup before locking. History and status commit together.
        queue = scope_faculty_records(ServiceRequest.objects.all(), request.user)
        ticket = get_object_or_404(queue.select_for_update(of=("self",)), pk=pk)
        incoming = self.get_serializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        status, revision, comment = (
            incoming.validated_data[field] for field in ("status", "expected_revision", "comment")
        )
        if revision != ticket.revision:
            raise Conflict("Заявку уже обновили. Откройте свежую версию.")
        if status not in TRANSITIONS.get(ticket.status, set()):
            raise ValidationError({"status": "Переход между этими статусами недоступен."})
        if status == ServiceRequest.Status.REJECTED and not comment:
            raise ValidationError({"comment": "Объясните студенту причину отказа."})
        ticket.status = status
        ticket.revision += 1
        ticket.save(update_fields=["status", "revision", "updated_at"])
        RequestEvent.objects.create(
            ticket=ticket,
            status=status,
            revision=ticket.revision,
            comment=comment,
            actor=request.user,
        )
        return Response(RequestSerializer(ticket).data)
