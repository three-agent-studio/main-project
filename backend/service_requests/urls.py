from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.StudentRequests.as_view()),
    path("requests/<uuid:pk>/", views.StudentRequestDetail.as_view()),
    path(
        "requests/<uuid:pk>/history/<uuid:event_id>/attachment/",
        views.StudentRequestAttachment.as_view(),
    ),
    path(
        "staff/requests/<uuid:pk>/history/<uuid:event_id>/attachment/",
        views.StaffRequestAttachment.as_view(),
    ),
    path("staff/requests/", views.StaffRequests.as_view()),
    path("staff/requests/<uuid:pk>/", views.StaffRequestDetail.as_view()),
    path("staff/requests/<uuid:pk>/status/", views.StaffRequestStatus.as_view()),
]
