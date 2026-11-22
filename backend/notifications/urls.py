from django.urls import path

from . import views

urlpatterns = [
    path("staff/announcements/", views.FacultyAnnouncementCreate.as_view()),
    path("notifications/", views.NoticeList.as_view()),
    path("notifications/<str:key>/read/", views.NoticeMarkRead.as_view()),
]
