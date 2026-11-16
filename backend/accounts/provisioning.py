"""Management-only provisioning. HTTP clients must never assign their own roles."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from academics.models import TeachingAssignment

from .models import TeacherProfile, User


@transaction.atomic
def create_teacher_account(*, username, password, group, full_name, subject):
    username = User.normalize_username(username.strip())
    if User.objects.filter(username=username).exists():
        raise ValidationError("Пользователь уже существует; пароль и права не изменены.")
    user = User(username=username)
    user.full_clean(exclude=["password"])
    validate_password(password, user)
    user.set_password(password)
    user.save()
    teacher = TeacherProfile(user=user, faculty=group.faculty, full_name=full_name)
    teacher.full_clean()
    teacher.save()
    today = timezone.localdate()
    year = today.year if today.month >= 9 else today.year - 1
    term = f"{year}/{year + 1} — {'1' if today.month >= 9 else '2'} семестр"
    assignment = TeachingAssignment(teacher=teacher, group=group, subject=subject, term=term)
    assignment.full_clean()
    assignment.save()
    return user
