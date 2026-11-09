from django.urls import re_path

from core.frontend import frontend_entry, unavailable

from .urls import urlpatterns as application_urls

urlpatterns = [
    re_path(r"^admin(?:/.*)?$", unavailable),
    *application_urls,
    # A misspelled API/asset URL must stay 404 instead of receiving HTML with status 200.
    re_path(r"^(?!(?:api|auth|admin|static|assets|health)(?:/|$))(?P<path>.*)$", frontend_entry),
]
