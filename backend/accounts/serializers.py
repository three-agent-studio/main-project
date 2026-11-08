from rest_framework import serializers

from .models import StaffProfile, StudentProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):
    group = serializers.CharField(source="group.name", read_only=True)
    faculty = serializers.CharField(source="group.faculty.name", read_only=True)
    programme = serializers.CharField(source="group.programme", read_only=True)
    course = serializers.IntegerField(source="group.course", read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["full_name", "group", "faculty", "programme", "course"]
        read_only_fields = fields


class StaffProfileSerializer(serializers.ModelSerializer):
    faculty = serializers.CharField(source="faculty.name", read_only=True)
    faculty_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = ["full_name", "faculty", "faculty_id"]
        read_only_fields = fields


class MeSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True, allow_null=True)
    staff_profile = StaffProfileSerializer(read_only=True, allow_null=True)
    roles = serializers.SerializerMethodField()

    def get_roles(self, obj) -> list[str]:
        roles = []
        if getattr(obj, "student_profile", None) is not None:
            roles.append("student")
        if getattr(obj, "staff_profile", None) is not None:
            roles.append("deanery_staff")
        return roles

    class Meta:
        model = User
        fields = ["id", "username", "student_profile", "staff_profile", "roles"]
        read_only_fields = fields
