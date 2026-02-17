"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = 'dev-secret-key-not-for-production'

ALLOWED_HOSTS = ['*']

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use console email backend in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable rate limiting in development
RATE_LIMIT_ENABLED = False
