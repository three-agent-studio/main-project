from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Faculty, StudentProfile, StudyGroup, User

admin.site.register(User, UserAdmin)
admin.site.register(Faculty)
admin.site.register(StudyGroup)
admin.site.register(StudentProfile)
