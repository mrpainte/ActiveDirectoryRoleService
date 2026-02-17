"""WSGI config for AD Manager project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ad_manager.settings.production')

application = get_wsgi_application()
