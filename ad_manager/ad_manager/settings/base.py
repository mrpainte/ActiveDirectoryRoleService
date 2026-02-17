"""
Base settings for AD Manager project.
All shared settings, AD/Celery/DB configuration.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-in-production')

DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'django_celery_beat',
    # Local apps
    'core',
    'accounts',
    'directory',
    'groups',
    'dns_manager',
    'gpo',
    'notifications',
    'audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.KerberosNegotiateMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RoleContextMiddleware',
    'core.middleware.AuditMiddleware',
    'core.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'ad_manager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.ad_context',
                'core.context_processors.role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ad_manager.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ad_manager'),
        'USER': os.environ.get('DB_USER', 'ad_manager'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Authentication
AUTHENTICATION_BACKENDS = [
    'accounts.backends.ADLDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Password validation (for Django admin, not AD users)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('TZ', 'UTC')
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Messages framework - Bootstrap CSS classes
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# ─── Active Directory / LDAP Configuration ───────────────────────────────────
AD_LDAP_SERVERS = os.environ.get('AD_LDAP_SERVERS', 'ldap://dc1.example.com').split(',')
AD_LDAP_USE_SSL = os.environ.get('AD_LDAP_USE_SSL', 'false').lower() == 'true'
AD_BASE_DN = os.environ.get('AD_BASE_DN', 'DC=example,DC=com')
AD_DOMAIN = os.environ.get('AD_DOMAIN', 'EXAMPLE')
AD_USER_SEARCH_BASE = os.environ.get('AD_USER_SEARCH_BASE', AD_BASE_DN)
AD_GROUP_SEARCH_BASE = os.environ.get('AD_GROUP_SEARCH_BASE', AD_BASE_DN)
AD_COMPUTER_SEARCH_BASE = os.environ.get('AD_COMPUTER_SEARCH_BASE', AD_BASE_DN)

# Service account for LDAP queries (read operations, user search before bind)
AD_BIND_DN = os.environ.get('AD_BIND_DN', '')
AD_BIND_PASSWORD = os.environ.get('AD_BIND_PASSWORD', '')

# Kerberos SSO (optional)
AD_KERBEROS_ENABLED = os.environ.get('AD_KERBEROS_ENABLED', 'false').lower() == 'true'
AD_KERBEROS_KEYTAB = os.environ.get('AD_KERBEROS_KEYTAB', '/etc/krb5.keytab')
AD_KERBEROS_SERVICE = os.environ.get('AD_KERBEROS_SERVICE', 'HTTP')

# LDAP connection pool settings
AD_LDAP_POOL_SIZE = int(os.environ.get('AD_LDAP_POOL_SIZE', '10'))
AD_LDAP_POOL_LIFETIME = int(os.environ.get('AD_LDAP_POOL_LIFETIME', '300'))
AD_LDAP_CONNECT_TIMEOUT = int(os.environ.get('AD_LDAP_CONNECT_TIMEOUT', '5'))
AD_LDAP_RECEIVE_TIMEOUT = int(os.environ.get('AD_LDAP_RECEIVE_TIMEOUT', '10'))

# ─── Celery Configuration ────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ─── Email / Notification Configuration ──────────────────────────────────────
NOTIFICATION_BACKEND = os.environ.get('NOTIFICATION_BACKEND', 'smtp')  # 'smtp' or 'ses'

# SMTP settings
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'false').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# AWS SES settings
AWS_SES_REGION = os.environ.get('AWS_SES_REGION', 'us-east-1')
AWS_SES_ACCESS_KEY_ID = os.environ.get('AWS_SES_ACCESS_KEY_ID', '')
AWS_SES_SECRET_ACCESS_KEY = os.environ.get('AWS_SES_SECRET_ACCESS_KEY', '')

# Password expiry notification settings
PASSWORD_EXPIRY_WARN_DAYS = [int(d) for d in os.environ.get('PASSWORD_EXPIRY_WARN_DAYS', '14,7,3,1').split(',')]

# ─── Rate Limiting ───────────────────────────────────────────────────────────
RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_REDIS_URL = os.environ.get('RATE_LIMIT_REDIS_URL', CELERY_BROKER_URL)
RATE_LIMIT_LOGIN_MAX = int(os.environ.get('RATE_LIMIT_LOGIN_MAX', '5'))
RATE_LIMIT_LOGIN_WINDOW = int(os.environ.get('RATE_LIMIT_LOGIN_WINDOW', '300'))  # seconds

# ─── Session Configuration ───────────────────────────────────────────────────
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', '28800'))  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
