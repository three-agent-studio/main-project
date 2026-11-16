from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Faculty, StaffProfile, StudentProfile, StudyGroup, TeacherProfile, User

admin.site.register(User, UserAdmin)
admin.site.register(Faculty)
admin.site.register(StudyGroup)
admin.site.register(StudentProfile)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "faculty"]
    list_filter = ["faculty"]
    search_fields = ["full_name", "user__username"]

    # Assigning a faculty grants business access. Ordinary admin permissions must
    # not let an employee widen their own scope; only superusers assign this role.
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(StaffProfileAdmin):
    list_display = ["full_name", "user", "faculty", "is_active"]
