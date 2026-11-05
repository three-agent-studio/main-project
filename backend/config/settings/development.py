from .base import *  # noqa: F403

DEBUG = True
# This key is ONLY for local development, never imported by production settings.
SECRET_KEY = SECRET_KEY or "local-development-only-not-for-deployment"  # noqa: F405
# Keep explicit LAN addresses supplied in .env; never enable a wildcard host policy.
ALLOWED_HOSTS = list(dict.fromkeys([
    "localhost", "127.0.0.1", "[::1]", "backend", "testserver",
    *ALLOWED_HOSTS,  # noqa: F405
]))
