from rest_framework import serializers

from .models import StudentProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):
    group = serializers.CharField(source="group.name", read_only=True)
    faculty = serializers.CharField(source="group.faculty.name", read_only=True)
    programme = serializers.CharField(source="group.programme", read_only=True)
    course = serializers.IntegerField(source="group.course", read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["full_name", "group", "faculty", "programme", "course"]
        read_only_fields = fields


class MeSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "student_profile"]
        read_only_fields = fields
