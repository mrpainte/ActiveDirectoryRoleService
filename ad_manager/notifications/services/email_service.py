"""Email sending service."""
import logging

from django.template import Template, Context
from django.utils import timezone

from notifications.models import NotificationConfig, EmailTemplate, SentNotification
from notifications.backends.smtp_backend import SMTPBackend
from notifications.backends.ses_backend import SESBackend

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending templated emails."""

    def __init__(self):
        self.config = NotificationConfig.get_config()

    def get_backend(self):
        """Return the appropriate email backend based on configuration."""
        if self.config.backend_type == NotificationConfig.BACKEND_SES:
            return SESBackend(self.config)
        return SMTPBackend(self.config)

    def send_template(self, template_name, recipient_email, context, recipient_dn=''):
        """Render and send an email template.

        Args:
            template_name: Name of the EmailTemplate to use.
            recipient_email: Recipient email address.
            context: Dict of template variables.
            recipient_dn: Optional AD distinguished name of recipient.

        Returns:
            The SentNotification record.
        """
        try:
            email_template = EmailTemplate.objects.get(
                name=template_name, is_active=True
            )
        except EmailTemplate.DoesNotExist:
            logger.error("Email template '%s' not found or inactive", template_name)
            return None

        # Render template strings with context
        tmpl_context = Context(context)

        rendered_subject = Template(email_template.subject).render(tmpl_context)
        rendered_html = Template(email_template.body_html).render(tmpl_context)
        rendered_text = Template(email_template.body_text).render(tmpl_context)

        # Create the notification record
        notification = SentNotification.objects.create(
            template=email_template,
            recipient_email=recipient_email,
            recipient_dn=recipient_dn,
            subject=rendered_subject,
            status=SentNotification.STATUS_PENDING,
            metadata=context if isinstance(context, dict) else {},
        )

        if not self.config.enabled:
            notification.status = SentNotification.STATUS_FAILED
            notification.error_message = 'Notifications are disabled'
            notification.save()
            return notification

        backend = self.get_backend()
        success, error = backend.send(
            recipient_email, rendered_subject, rendered_html, rendered_text
        )

        if success:
            notification.status = SentNotification.STATUS_SENT
            notification.sent_at = timezone.now()
        else:
            notification.status = SentNotification.STATUS_FAILED
            notification.error_message = error

        notification.save()
        return notification

    def send_raw(self, recipient_email, subject, body_html, body_text,
                 recipient_dn='', metadata=None):
        """Send an ad-hoc email without a stored template.

        Used for admin-composed emails (e.g., announcements to groups).
        """
        notification = SentNotification.objects.create(
            template=None,
            recipient_email=recipient_email,
            recipient_dn=recipient_dn,
            subject=subject,
            status=SentNotification.STATUS_PENDING,
            metadata=metadata or {},
        )

        if not self.config.enabled:
            notification.status = SentNotification.STATUS_FAILED
            notification.error_message = 'Notifications are disabled'
            notification.save()
            return notification

        backend = self.get_backend()
        success, error = backend.send(
            recipient_email, subject, body_html, body_text
        )

        if success:
            notification.status = SentNotification.STATUS_SENT
            notification.sent_at = timezone.now()
        else:
            notification.status = SentNotification.STATUS_FAILED
            notification.error_message = error

        notification.save()
        return notification
