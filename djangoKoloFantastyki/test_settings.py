"""Isolated test configuration; opt into PostgreSQL with TEST_POSTGRES=True."""

import os

os.environ["READ_DOT_ENV"] = "False"
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-only-key-never-use-for-a-deployment"
if os.environ.get("TEST_POSTGRES", "").lower() != "true":
    os.environ["DATABASE_ENGINE"] = "sqlite3"

from .settings import *  # noqa: E402,F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
