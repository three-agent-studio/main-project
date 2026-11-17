from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.access import require_student, scope_student_records
from accounts.models import StudentProfile

from .models import AcademicActivity, Assessment, TeachingAssignment
from .teaching_access import IsTeacher, teacher_activities, teacher_assignments
from .teaching_serializers import (
    ActivityPublicSerializer,
    ActivityWriteSerializer,
    AssessmentSerializer,
    AssignmentSerializer,
    ResultInputSerializer,
    RosterSerializer,
)
from .teaching_services import set_result

ACTIVITY_RELATED = ("assignment__teacher", "assignment__group")


class TeacherAssignmentList(ListAPIView):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TeachingAssignment.objects.none()
        return teacher_assignments(self.request.user).select_related("group")


class TeacherActivityViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = ActivityWriteSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AcademicActivity.objects.none()
        qs = teacher_activities(self.request.user).select_related(*ACTIVITY_RELATED)
        if self.request.method == "PATCH":
            qs = qs.select_for_update()
        assignment = self.request.query_params.get("assignment")
        if assignment is not None:
            try:
                qs = qs.filter(assignment_id=int(assignment))
            except (ValueError, OverflowError):
                raise ValidationError(
                    {"assignment": "Ожидается идентификатор назначения."}
                ) from None
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        assignment = get_object_or_404(
            teacher_assignments(self.request.user).select_for_update(),
            pk=serializer.validated_data["assignment"].pk,
        )
        serializer.save(assignment=assignment)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class TeacherRoster(ListAPIView):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = RosterSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StudentProfile.objects.none()
        activity = get_object_or_404(teacher_activities(self.request.user), pk=self.kwargs["pk"])
        results = Assessment.objects.filter(activity=activity).select_related(
            "activity__assignment__teacher", "activity__assignment__group"
        )
        return (
            StudentProfile.objects.filter(group_id=activity.assignment.group_id)
            .order_by("full_name", "id")
            .prefetch_related(Prefetch("assessments", queryset=results, to_attr="grade_results"))
        )


class TeacherResults(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Assessment.objects.none()
        activity = get_object_or_404(teacher_activities(self.request.user), pk=self.kwargs["pk"])
        return Assessment.objects.filter(
            activity=activity, student__group_id=activity.assignment.group_id
        ).select_related("activity__assignment__teacher", "activity__assignment__group")

    @extend_schema(
        request=ResultInputSerializer,
        responses={200: AssessmentSerializer, 201: AssessmentSerializer},
    )
    def post(self, request, *args, **kwargs):
        data = ResultInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result, created = set_result(request.user, self.kwargs["pk"], **data.validated_data)
        return Response(
            AssessmentSerializer(result).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class StudentActivities(ListAPIView):
    serializer_class = ActivityPublicSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AcademicActivity.objects.none()
        student = require_student(self.request.user)
        return AcademicActivity.objects.filter(
            assignment__group_id=student.group_id
        ).select_related(*ACTIVITY_RELATED)


class StudentAssessments(ListAPIView):
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Assessment.objects.none()
        require_student(self.request.user)
        qs = scope_student_records(Assessment.objects.all(), self.request.user).select_related(
            "activity__assignment__teacher", "activity__assignment__group"
        )
        debt = self.request.query_params.get("debt")
        term = self.request.query_params.get("term")
        if term:
            qs = qs.filter(activity__assignment__term=term)
        if debt is not None:
            if debt not in {"true", "false"}:
                raise ValidationError({"debt": "Допустимо true или false."})
            condition = Q(status__in=["debt", "failed"]) | Q(score=2)
            qs = qs.filter(condition) if debt == "true" else qs.exclude(condition)
        return qs
