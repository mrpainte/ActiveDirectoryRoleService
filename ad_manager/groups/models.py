"""Models for delegated group management."""
from django.conf import settings
from django.db import models


class DelegatedGroup(models.Model):
    """An AD group that has been delegated for management by GroupManagers."""

    group_dn = models.TextField(unique=True)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class GroupManagerAssignment(models.Model):
    """Assignment of a user as a manager for a delegated group."""

    delegated_group = models.ForeignKey(
        DelegatedGroup,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_assignments',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='group_assignments_made',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('delegated_group', 'user')

    def __str__(self):
        return f"{self.user} -> {self.delegated_group}"
