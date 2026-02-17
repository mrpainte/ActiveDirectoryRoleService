"""Audit logging models."""
from django.conf import settings
from django.db import models

from core.constants import (
    AUDIT_CATEGORY_ADMIN,
    AUDIT_CATEGORY_AUTH,
    AUDIT_CATEGORY_DNS,
    AUDIT_CATEGORY_GPO,
    AUDIT_CATEGORY_GROUP,
    AUDIT_CATEGORY_NOTIFICATION,
    AUDIT_CATEGORY_USER,
)

CATEGORY_CHOICES = [
    (AUDIT_CATEGORY_AUTH, 'Authentication'),
    (AUDIT_CATEGORY_USER, 'User Management'),
    (AUDIT_CATEGORY_GROUP, 'Group Management'),
    (AUDIT_CATEGORY_DNS, 'DNS Management'),
    (AUDIT_CATEGORY_GPO, 'GPO'),
    (AUDIT_CATEGORY_NOTIFICATION, 'Notification'),
    (AUDIT_CATEGORY_ADMIN, 'Admin'),
]


class AuditEntry(models.Model):
    """Immutable audit log entry."""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='audit_entries',
    )
    username = models.CharField(max_length=150)
    action = models.CharField(max_length=100, db_index=True)
    category = models.CharField(
        max_length=50, db_index=True, choices=CATEGORY_CHOICES
    )
    target_dn = models.TextField(blank=True, default='')
    detail = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'audit entries'
        indexes = [
            models.Index(
                fields=['category', 'timestamp'],
                name='audit_category_ts_idx',
            ),
            models.Index(
                fields=['user', 'timestamp'],
                name='audit_user_ts_idx',
            ),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.username}: {self.action}"
