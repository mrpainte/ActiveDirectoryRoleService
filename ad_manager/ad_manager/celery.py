"""Celery app definition for AD Manager."""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ad_manager.settings.development')

app = Celery('ad_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
