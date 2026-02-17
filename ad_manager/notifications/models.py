"""Notification models."""
from django.db import models


class NotificationConfigManager(models.Manager):
    """Manager that ensures only one NotificationConfig exists."""

    def get_config(self):
        """Return the singleton config, creating a default if needed."""
        config, _ = self.get_or_create(pk=1)
        return config


class NotificationConfig(models.Model):
    """Singleton notification configuration."""

    BACKEND_SMTP = 'smtp'
    BACKEND_SES = 'ses'
    BACKEND_CHOICES = [
        (BACKEND_SMTP, 'SMTP'),
        (BACKEND_SES, 'Amazon SES'),
    ]

    backend_type = models.CharField(
        max_length=10, choices=BACKEND_CHOICES, default=BACKEND_SMTP
    )

    # SMTP settings
    smtp_host = models.CharField(max_length=255, blank=True, default='localhost')
    smtp_port = models.PositiveIntegerField(default=25)
    smtp_username = models.CharField(max_length=255, blank=True, default='')
    smtp_password = models.CharField(max_length=255, blank=True, default='')
    smtp_use_tls = models.BooleanField(default=False)

    # SES settings
    ses_region = models.CharField(max_length=50, blank=True, default='us-east-1')
    ses_access_key_id = models.CharField(max_length=255, blank=True, default='')
    ses_secret_access_key = models.CharField(max_length=255, blank=True, default='')

    from_email = models.EmailField(default='noreply@example.com')
    warn_days = models.CharField(
        max_length=50,
        default='14,7,3,1',
        help_text='Comma-separated days before password expiry to send warnings.',
    )
    enabled = models.BooleanField(default=True)

    objects = NotificationConfigManager()

    class Meta:
        verbose_name = 'notification configuration'
        verbose_name_plural = 'notification configuration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion of singleton

    @classmethod
    def get_config(cls):
        return cls.objects.get_config()

    def get_warn_days_list(self):
        """Return warn_days as a list of integers."""
        try:
            return sorted(
                [int(d.strip()) for d in self.warn_days.split(',') if d.strip()],
                reverse=True,
            )
        except (ValueError, AttributeError):
            return [14, 7, 3, 1]

    def __str__(self):
        return f"Notification Config ({self.get_backend_type_display()})"


class EmailTemplate(models.Model):
    """Configurable email template."""

    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    body_html = models.TextField(help_text='HTML body. Use Django template variables.')
    body_text = models.TextField(
        help_text='Plain text fallback body. Use Django template variables.'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of available template variables.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SentNotification(models.Model):
    """Record of a sent notification."""

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    template = models.ForeignKey(
        EmailTemplate,
        null=True,
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
    )
    recipient_email = models.EmailField()
    recipient_dn = models.TextField(blank=True, default='')
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    error_message = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient_email} - {self.subject} ({self.status})"
