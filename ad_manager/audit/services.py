"""Audit logging service."""
import logging

from audit.models import AuditEntry

logger = logging.getLogger(__name__)


class AuditLogger:
    """Convenience class for creating audit log entries."""

    @staticmethod
    def log(user, action, category, target_dn='', detail=None, ip_address=None, success=True):
        """Create an audit log entry.

        Args:
            user: Django User instance or None for system actions.
            action: Action identifier (e.g. 'user.login', 'group.add_member').
            category: Audit category constant.
            target_dn: Distinguished name of the AD object acted upon.
            detail: Dict of arbitrary metadata.
            ip_address: Client IP address.
            success: Whether the action succeeded.

        Returns:
            The created AuditEntry.
        """
        if detail is None:
            detail = {}

        username = ''
        if user and hasattr(user, 'username'):
            username = user.username

        try:
            entry = AuditEntry.objects.create(
                user=user if user and hasattr(user, 'pk') and user.pk else None,
                username=username,
                action=action,
                category=category,
                target_dn=target_dn,
                detail=detail,
                ip_address=ip_address,
                success=success,
            )
            return entry
        except Exception:
            logger.exception("Failed to create audit log entry")
            return None

    @staticmethod
    def log_from_request(request, action, category, target_dn='', detail=None, success=True):
        """Create an audit log entry from a Django request.

        Extracts user and IP address from the request object.
        The client_ip attribute is set by core.middleware.AuditMiddleware.
        """
        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None

        ip_address = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR'))

        return AuditLogger.log(
            user=user,
            action=action,
            category=category,
            target_dn=target_dn,
            detail=detail,
            ip_address=ip_address,
            success=success,
        )
