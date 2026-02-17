"""Amazon SES email backend."""
import logging

logger = logging.getLogger(__name__)


class SESBackend:
    """Send emails via Amazon SES using boto3."""

    def __init__(self, config):
        """Initialize with a NotificationConfig instance."""
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                'ses',
                region_name=self.config.ses_region,
                aws_access_key_id=self.config.ses_access_key_id or None,
                aws_secret_access_key=self.config.ses_secret_access_key or None,
            )
        return self._client

    def send(self, to_email, subject, html_body, text_body):
        """Send an email via SES.

        Returns:
            Tuple of (success: bool, error_message: str).
        """
        try:
            client = self._get_client()
            client.send_email(
                Source=self.config.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    },
                },
            )
            return True, ''
        except Exception as exc:
            logger.exception("SES send failed to %s", to_email)
            return False, str(exc)
