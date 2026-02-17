"""Service for Group Policy Object operations."""
import logging

from django.conf import settings

from directory.services.base_service import BaseLDAPService, LDAPServiceError

logger = logging.getLogger(__name__)

GPO_ATTRIBUTES = [
    'displayName',
    'distinguishedName',
    'gPCFileSysPath',
    'versionNumber',
    'flags',
    'whenCreated',
    'whenChanged',
    'cn',
    'name',
]


class GPOService(BaseLDAPService):
    """LDAP operations for Group Policy Objects."""

    def _get_gpo_base(self):
        """Return the search base for GPOs."""
        return f'CN=Policies,CN=System,{settings.AD_BASE_DN}'

    def list_gpos(self):
        """List all Group Policy Objects."""
        try:
            entries = self.search(
                self._get_gpo_base(),
                '(objectClass=groupPolicyContainer)',
                GPO_ATTRIBUTES,
            )
            for entry in entries:
                flags = entry['attributes'].get('flags', 0)
                entry['status'] = self.get_gpo_status(flags)
            return entries
        except LDAPServiceError:
            logger.exception("Failed to list GPOs")
            raise

    def get_gpo(self, dn):
        """Get a single GPO with full attributes."""
        try:
            entry = self.get(dn, GPO_ATTRIBUTES)
            if entry:
                flags = entry['attributes'].get('flags', 0)
                entry['status'] = self.get_gpo_status(flags)
            return entry
        except LDAPServiceError:
            logger.exception("Failed to get GPO %s", dn)
            raise

    def get_linked_ous(self, gpo_dn):
        """Search for OUs where gPLink contains this GPO's DN."""
        # Extract the GPO GUID from the DN for matching in gPLink
        # gPLink format: [LDAP://cn={GUID},cn=policies,cn=system,DC=...;0]
        safe_dn = gpo_dn.replace('\\', '\\5c').replace('*', '\\2a').replace(
            '(', '\\28').replace(')', '\\29').replace('\x00', '\\00')
        ldap_filter = f'(&(objectClass=organizationalUnit)(gPLink=*{safe_dn}*))'
        try:
            return self.search(
                settings.AD_BASE_DN,
                ldap_filter,
                ['ou', 'distinguishedName', 'name', 'description'],
            )
        except LDAPServiceError:
            logger.exception("Failed to find linked OUs for GPO %s", gpo_dn)
            raise

    @staticmethod
    def get_gpo_status(flags):
        """Interpret GPO flags value.

        Flags:
            0 = All settings enabled
            1 = User configuration disabled
            2 = Computer configuration disabled
            3 = All settings disabled
        """
        if isinstance(flags, list):
            flags = flags[0] if flags else 0
        try:
            flags = int(flags)
        except (ValueError, TypeError):
            flags = 0

        if flags == 0:
            return {'code': 0, 'label': 'Enabled', 'badge': 'success'}
        elif flags == 1:
            return {'code': 1, 'label': 'User Config Disabled', 'badge': 'warning'}
        elif flags == 2:
            return {'code': 2, 'label': 'Computer Config Disabled', 'badge': 'warning'}
        elif flags == 3:
            return {'code': 3, 'label': 'All Disabled', 'badge': 'danger'}
        else:
            return {'code': flags, 'label': f'Unknown ({flags})', 'badge': 'secondary'}
