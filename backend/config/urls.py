from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from accounts.views import StudentLoginView
from core.views import liveness, readiness

urlpatterns = [
    path("health/live/", liveness),
    path("health/ready/", readiness),
    path("auth/login/", StudentLoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),  # POST + CSRF; GET never changes a session.
    path("admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("academics.urls")),
    # Domain owners add include() here once their API contract is reviewed.
]
