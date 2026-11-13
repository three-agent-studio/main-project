from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if len(SECRET_KEY) < 50 or not ALLOWED_HOSTS or not DATABASES["default"]["PASSWORD"]:  # noqa: F405
    raise ImproperlyConfigured("Set a long DJANGO_SECRET_KEY, hosts and database password.")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Only deploy behind a trusted proxy that overwrites this header. Never expose Gunicorn.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
