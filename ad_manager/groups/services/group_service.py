"""Service for Active Directory group operations."""
import logging

from django.conf import settings
from ldap3 import MODIFY_ADD, MODIFY_DELETE

from directory.services.base_service import BaseLDAPService, LDAPServiceError
from groups.models import DelegatedGroup, GroupManagerAssignment
from core.constants import ROLE_ADMIN, ROLE_HELPDESK

logger = logging.getLogger(__name__)

GROUP_ATTRIBUTES = [
    'cn',
    'description',
    'member',
    'distinguishedName',
    'groupType',
    'managedBy',
    'whenCreated',
]


class GroupService(BaseLDAPService):
    """LDAP operations for AD group management."""

    def list_groups(self, search_base=None, search_filter=None, page=1,
                    page_size=25):
        """List AD groups with pagination."""
        base = search_base or settings.AD_GROUP_SEARCH_BASE
        ldap_filter = search_filter or '(objectClass=group)'
        entries = self.search(base, ldap_filter, GROUP_ATTRIBUTES)
        # Manual pagination over results
        start = (page - 1) * page_size
        end = start + page_size
        return {
            'groups': entries[start:end],
            'total': len(entries),
            'page': page,
            'page_size': page_size,
            'has_next': end < len(entries),
            'has_prev': page > 1,
        }

    def get_group(self, dn):
        """Get a single group with all attributes."""
        return self.get(dn, GROUP_ATTRIBUTES)

    def search_groups(self, query):
        """Search groups by name or description."""
        safe_query = query.replace('\\', '\\5c').replace('*', '\\2a').replace(
            '(', '\\28').replace(')', '\\29').replace('\x00', '\\00')
        ldap_filter = (
            f'(&(objectClass=group)(|(cn=*{safe_query}*)'
            f'(description=*{safe_query}*)))'
        )
        return self.search(
            settings.AD_GROUP_SEARCH_BASE, ldap_filter, GROUP_ATTRIBUTES
        )

    def get_members(self, dn):
        """Get members of a group with resolved display names."""
        group = self.get(dn, ['member'])
        if not group:
            return []
        members_raw = group['attributes'].get('member', [])
        if isinstance(members_raw, str):
            members_raw = [members_raw]
        members = []
        for member_dn in members_raw:
            display_name = member_dn.split(',')[0]
            if display_name.upper().startswith('CN='):
                display_name = display_name[3:]
            try:
                entry = self.get(member_dn, ['displayName', 'sAMAccountName'])
                if entry:
                    display_name = (
                        entry['attributes'].get('displayName', '') or
                        entry['attributes'].get('sAMAccountName', '') or
                        display_name
                    )
            except LDAPServiceError:
                pass
            members.append({
                'dn': member_dn,
                'display_name': display_name,
            })
        return members

    def add_member(self, group_dn, member_dn):
        """Add a member to a group."""
        changes = {'member': [(MODIFY_ADD, [member_dn])]}
        try:
            return self.modify(group_dn, changes)
        except LDAPServiceError:
            logger.exception(
                "Failed to add member %s to group %s", member_dn, group_dn
            )
            raise

    def remove_member(self, group_dn, member_dn):
        """Remove a member from a group."""
        changes = {'member': [(MODIFY_DELETE, [member_dn])]}
        try:
            return self.modify(group_dn, changes)
        except LDAPServiceError:
            logger.exception(
                "Failed to remove member %s from group %s",
                member_dn, group_dn,
            )
            raise

    @staticmethod
    def can_manage_group(user, group_dn):
        """Check if a user can manage a specific group.

        Admins and HelpDesk can manage any group. GroupManagers can
        only manage groups that have been delegated to them.
        """
        if user.is_superuser:
            return True
        try:
            profile = user.userprofile
            roles = set(profile.roles.values_list('name', flat=True))
        except Exception:
            return False
        if ROLE_ADMIN in roles or ROLE_HELPDESK in roles:
            return True
        # Check delegated assignment
        return GroupManagerAssignment.objects.filter(
            user=user,
            delegated_group__group_dn=group_dn,
            delegated_group__enabled=True,
        ).exists()
