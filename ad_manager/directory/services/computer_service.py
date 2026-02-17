"""Service for Active Directory computer object operations."""
import logging

from django.conf import settings

from core.constants import DEFAULT_PAGE_SIZE
from .base_service import BaseLDAPService

logger = logging.getLogger(__name__)

COMPUTER_ATTRIBUTES = [
    'cn',
    'dNSHostName',
    'operatingSystem',
    'operatingSystemVersion',
    'whenCreated',
    'lastLogonTimestamp',
    'userAccountControl',
    'distinguishedName',
    'description',
    'objectGUID',
]


class ComputerService(BaseLDAPService):
    """Operations on AD computer objects."""

    def list_computers(self, search_base=None, search_filter=None, page=1,
                       page_size=DEFAULT_PAGE_SIZE):
        """List computer objects with pagination."""
        base = search_base or settings.AD_COMPUTER_SEARCH_BASE
        ldap_filter = search_filter or '(objectClass=computer)'
        all_entries = self.search(base, ldap_filter, COMPUTER_ATTRIBUTES)
        total = len(all_entries)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            'entries': all_entries[start:end],
            'total': total,
            'page': page,
            'page_size': page_size,
            'num_pages': (total + page_size - 1) // page_size,
        }

    def get_computer(self, dn):
        """Get a single computer with all attributes."""
        return self.get(dn, ['*'])

    def search_computers(self, query):
        """Search computers by name or description."""
        escaped = query.replace('\\', '\\5c').replace('*', '\\2a').replace(
            '(', '\\28').replace(')', '\\29').replace('\x00', '\\00')
        ldap_filter = (
            '(&(objectClass=computer)'
            '(|(cn=*{q}*)(dNSHostName=*{q}*)(description=*{q}*)))'
        ).format(q=escaped)
        base = settings.AD_COMPUTER_SEARCH_BASE
        return self.search(base, ldap_filter, COMPUTER_ATTRIBUTES)
