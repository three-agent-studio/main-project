from .base import *  # noqa: F403

DEBUG = True
# This key is ONLY for local development, never imported by production settings.
SECRET_KEY = SECRET_KEY or "local-development-only-not-for-deployment"  # noqa: F405
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "backend", "testserver"]
