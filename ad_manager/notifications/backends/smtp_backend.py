"""SMTP email backend."""
import logging

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


class SMTPBackend:
    """Send emails via SMTP using Django's EmailMultiAlternatives."""

    def __init__(self, config):
        """Initialize with a NotificationConfig instance."""
        self.config = config

    def send(self, to_email, subject, html_body, text_body):
        """Send an email.

        Returns:
            Tuple of (success: bool, error_message: str).
        """
        try:
            connection = EmailBackend(
                host=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_username or None,
                password=self.config.smtp_password or None,
                use_tls=self.config.smtp_use_tls,
                fail_silently=False,
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=self.config.from_email,
                to=[to_email],
                connection=connection,
            )
            msg.attach_alternative(html_body, 'text/html')
            msg.send()

            return True, ''
        except Exception as exc:
            logger.exception("SMTP send failed to %s", to_email)
            return False, str(exc)
