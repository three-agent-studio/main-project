"""Server-side access boundaries shared by academics and service_requests.

Always scope a queryset BEFORE list/get/update/delete. An object permission alone does
not filter DRF lists, and UUIDs or a hidden navigation item are not authorization.
"""

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from rest_framework.permissions import BasePermission

from .models import StaffProfile, StudentProfile


def is_active_user(user):
    return bool(user and user.is_authenticated and user.is_active)


def staff_faculty_id(user):
    if not is_active_user(user):
        return None
    # Read the assignment from the DB: an admin revocation must take effect next request.
    # Neither is_staff nor is_superuser implicitly grants business access to all faculties.
    return StaffProfile.objects.filter(user_id=user.pk).values_list("faculty_id", flat=True).first()


def require_student(user):
    """Use on create: set the owner from this result, never from client-supplied student_id."""
    if is_active_user(user):
        profile = StudentProfile.objects.select_related("group__faculty").filter(user_id=user.pk)
        if student := profile.first():
            return student
    raise PermissionDenied("Для этого действия требуется профиль студента.")


def scope_student_records(queryset, user, *, student_path="student"):
    """Scope models linked to StudentProfile (or StudentProfile itself with student_path='').

    A separate faculty scope is required for employee endpoints: personal grades
    must not become accessible simply because a new role was assigned.
    These keyword arguments are developer configuration, never query parameters.
    """
    if not is_active_user(user):
        return queryset.none()
    prefix = f"{student_path}__" if student_path else ""
    return queryset.filter(Q(**{f"{prefix}user_id": user.pk}))


def scope_faculty_records(queryset, user, *, student_path="student"):
    """For employee endpoints only; no personal-owner OR that would widen faculty scope."""
    faculty_id = staff_faculty_id(user)
    if faculty_id is None:
        return queryset.none()
    prefix = f"{student_path}__" if student_path else ""
    return queryset.filter(**{f"{prefix}group__faculty_id": faculty_id})


class IsDeaneryStaff(BasePermission):
    """Endpoint gate; faculty-scoped querysets are still required for lists and objects."""

    message = "Доступ разрешён сотрудникам деканата."

    def has_permission(self, request, view):
        return staff_faculty_id(request.user) is not None
