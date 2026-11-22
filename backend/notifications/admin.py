from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "faculty", "published_at")
    list_filter = ("faculty",)
    search_fields = ("title", "message")
