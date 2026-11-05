from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Authentication identity. Student data belongs in StudentProfile, not in the session."""


class Faculty(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


class StudyGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="groups")
    programme = models.CharField(max_length=200)
    course = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(course__gte=1, course__lte=8), name="group_course_1_to_8"
        )]

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=250)
    group = models.ForeignKey(StudyGroup, on_delete=models.PROTECT, related_name="students")

    def __str__(self):
        return self.full_name
