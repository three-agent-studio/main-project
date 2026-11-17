from django.db.models import F
from rest_framework.permissions import BasePermission

from accounts.access import is_active_user
from accounts.models import TeacherProfile

from .models import AcademicActivity, TeachingAssignment


def teacher_id(user):
    if not is_active_user(user):
        return None
    return (
        TeacherProfile.objects.filter(user_id=user.pk, is_active=True)
        .values_list("pk", flat=True)
        .first()
    )


class IsTeacher(BasePermission):
    message = "Требуется активная роль преподавателя."

    def has_permission(self, request, view):
        return teacher_id(request.user) is not None


def teacher_assignments(user):
    # Re-read grants on every request: a cached /me response is not authority.
    return TeachingAssignment.objects.filter(
        teacher_id=teacher_id(user),
        is_active=True,
        teacher__is_active=True,
        teacher__faculty_id=F("group__faculty_id"),
    )


def teacher_activities(user):
    return AcademicActivity.objects.filter(assignment__in=teacher_assignments(user))
