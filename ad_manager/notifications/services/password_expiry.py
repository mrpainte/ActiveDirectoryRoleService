"""Password expiry checking service."""
import logging
from datetime import datetime, timedelta

from django.utils import timezone

from core.constants import AD_EPOCH_DIFF
from notifications.models import NotificationConfig, SentNotification
from notifications.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PasswordExpiryChecker:
    """Check AD users for expiring passwords and send notifications."""

    TEMPLATE_NAME = 'password_expiry'

    def __init__(self):
        self.config = NotificationConfig.get_config()
        self.email_service = EmailService()

    def check_all_users(self):
        """Check all AD users for expiring passwords and send warnings.

        Uses the directory app's UserService to query AD for users
        whose passwords are approaching expiration.
        """
        if not self.config.enabled:
            logger.info("Notifications disabled, skipping password expiry check")
            return

        warn_days = self.config.get_warn_days_list()
        if not warn_days:
            return

        max_pwd_age = self._get_max_password_age()
        if max_pwd_age is None:
            logger.warning("Could not determine max password age from AD")
            return

        try:
            from directory.services import UserService
            user_service = UserService()
            users = user_service.search_users('*')
        except Exception:
            logger.exception("Failed to query AD users for password expiry check")
            return

        now = timezone.now()

        for user_data in users:
            pwd_last_set = user_data.get('pwdLastSet')
            if not pwd_last_set:
                continue

            expiry_date = self._calculate_expiry(pwd_last_set, max_pwd_age)
            if expiry_date is None:
                continue

            days_until_expiry = (expiry_date - now).days

            if days_until_expiry < 0:
                continue

            # Find the matching warn threshold
            matched_threshold = None
            for threshold in warn_days:
                if days_until_expiry <= threshold:
                    matched_threshold = threshold

            if matched_threshold is None:
                continue

            email = user_data.get('mail') or user_data.get('userPrincipalName')
            if not email:
                continue

            dn = user_data.get('distinguishedName', '')
            display_name = user_data.get('displayName') or user_data.get('cn', '')

            # Avoid duplicate notifications for the same user/threshold
            already_sent = SentNotification.objects.filter(
                recipient_dn=dn,
                status=SentNotification.STATUS_SENT,
                metadata__days_threshold=matched_threshold,
                created_at__date=now.date(),
            ).exists()

            if already_sent:
                continue

            self.email_service.send_template(
                self.TEMPLATE_NAME,
                email,
                context={
                    'display_name': display_name,
                    'days_until_expiry': days_until_expiry,
                    'expiry_date': expiry_date.strftime('%B %d, %Y'),
                    'days_threshold': matched_threshold,
                },
                recipient_dn=dn,
            )

        logger.info("Password expiry check completed")

    def _calculate_expiry(self, pwd_last_set, max_pwd_age):
        """Calculate password expiry date from AD timestamps.

        Args:
            pwd_last_set: AD pwdLastSet value (Windows FILETIME, 100-nanosecond
                intervals since Jan 1, 1601).
            max_pwd_age: Max password age in days.

        Returns:
            datetime or None.
        """
        try:
            if isinstance(pwd_last_set, str):
                pwd_last_set = int(pwd_last_set)

            if pwd_last_set == 0:
                return None

            # Convert Windows FILETIME to Unix timestamp
            unix_ts = (pwd_last_set / 10_000_000) - AD_EPOCH_DIFF
            pwd_set_date = datetime.utcfromtimestamp(unix_ts)
            pwd_set_date = timezone.make_aware(pwd_set_date, timezone.utc)

            return pwd_set_date + timedelta(days=max_pwd_age)
        except (ValueError, TypeError, OSError):
            logger.debug("Could not parse pwdLastSet: %s", pwd_last_set)
            return None

    def _get_max_password_age(self):
        """Query AD domain policy for maxPwdAge.

        Returns:
            Max password age in days, or None if unavailable.
        """
        try:
            from directory.services import UserService
            user_service = UserService()
            result = user_service.get_domain_policy()
            if result and 'maxPwdAge' in result:
                # maxPwdAge is stored as negative 100-nanosecond intervals
                max_pwd_age_raw = int(result['maxPwdAge'])
                if max_pwd_age_raw < 0:
                    max_pwd_age_raw = abs(max_pwd_age_raw)
                return max_pwd_age_raw / (10_000_000 * 60 * 60 * 24)
        except Exception:
            logger.exception("Failed to get max password age from AD")

        # Fallback: 90 days is a common default
        return 90
