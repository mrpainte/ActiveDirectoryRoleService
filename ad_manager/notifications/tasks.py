"""Celery tasks for notifications."""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='notifications.check_password_expirations')
def check_password_expirations():
    """Check all AD users for expiring passwords and send notifications.

    Designed to be scheduled daily via celery-beat.
    """
    from notifications.services.password_expiry import PasswordExpiryChecker

    checker = PasswordExpiryChecker()
    checker.check_all_users()


@shared_task(name='notifications.send_notification_email')
def send_notification_email(template_name, recipient_email, context, recipient_dn=''):
    """Send a single email asynchronously via the configured backend.

    Args:
        template_name: Name of the EmailTemplate to use.
        recipient_email: Recipient email address.
        context: Dict of template variables.
        recipient_dn: Optional AD distinguished name of recipient.
    """
    from notifications.services.email_service import EmailService

    service = EmailService()
    service.send_template(template_name, recipient_email, context, recipient_dn)


@shared_task(name='notifications.send_bulk_email')
def send_bulk_email(subject, body_html, body_text, recipient_emails, metadata=None):
    """Send an ad-hoc email to a list of recipients.

    Used by the admin "Send Email" feature for group announcements etc.
    Each recipient gets their own SentNotification record.
    """
    from notifications.services.email_service import EmailService

    service = EmailService()
    sent = 0
    failed = 0
    for email in recipient_emails:
        try:
            result = service.send_raw(email, subject, body_html, body_text,
                                      metadata=metadata or {})
            if result and result.status == 'sent':
                sent += 1
            else:
                failed += 1
        except Exception:
            logger.exception("Failed to send bulk email to %s", email)
            failed += 1

    logger.info("Bulk email complete: %d sent, %d failed, subject='%s'",
                sent, failed, subject)
