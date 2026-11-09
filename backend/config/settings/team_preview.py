"""HTTPS review endpoint on a developer Mac; no development server is published."""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from . import production
from .production import *  # noqa: F403

ROOT_URLCONF = "config.urls_team_preview"
FRONTEND_DIST = Path(BASE_DIR).parent / "frontend" / "dist"  # noqa: F405
if not (FRONTEND_DIST / "index.html").is_file():
    raise ImproperlyConfigured("Build frontend before starting the shared preview.")
MIDDLEWARE = production.MIDDLEWARE.copy()
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
WHITENOISE_ROOT = FRONTEND_DIST
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_ALLOW_ALL_ORIGINS = False
# Temporary service-owned hostnames must not receive a year-long HSTS policy.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_NAME = "deanery_preview_session"
CSRF_COOKIE_NAME = "deanery_preview_csrf"
