import os

from .base import *  # noqa: F403

SECRET_KEY = "test-only-key"
ALLOWED_HOSTS = ["testserver", "localhost"]
# CI exercises PostgreSQL; SQLite is an explicit fast unit-test option, never a prod fallback.
if os.environ.get("TEST_POSTGRES") != "1":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
