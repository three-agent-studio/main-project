from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.access import IsDeaneryStaff, require_student, staff_faculty_id

from .feed import feed, rows
from .models import Announcement, NoticeRead


class NoticeSerializer(serializers.Serializer):
    key = serializers.CharField()
    category = serializers.CharField()
    headline = serializers.CharField()
    body = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    read = serializers.BooleanField()


class NoticeList(generics.ListAPIView):
    serializer_class = NoticeSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NoticeRead.objects.none()
        return feed(require_student(self.request.user))


class NoticeMarkRead(generics.GenericAPIView):
    serializer_class = NoticeSerializer

    @extend_schema(request=None, responses={204: None})
    def post(self, request, key):
        student = require_student(request.user)
        source = key.partition("-")[0]
        if source not in {"news", "schedule", "request", "deadline"} or len(key) > 100:
            raise Http404
        if not rows(source, student, key).exists():
            raise Http404
        NoticeRead.objects.get_or_create(user=request.user, key=key)
        return Response(status=204)


class FacultyAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "title", "message", "published_at")
        read_only_fields = ("id", "published_at")
        extra_kwargs = {"message": {"max_length": 1500}}


class FacultyAnnouncementCreate(generics.CreateAPIView):
    permission_classes = [IsDeaneryStaff]
    serializer_class = FacultyAnnouncementSerializer

    def perform_create(self, serializer):
        faculty_id = staff_faculty_id(self.request.user)
        if faculty_id is None:
            raise PermissionDenied()
        # API never accepts faculty_id. A global announcement is admin-only.
        serializer.save(faculty_id=faculty_id)
