from django.urls import path

from .views import MeView, csrf_token

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("csrf/", csrf_token, name="csrf"),
]
