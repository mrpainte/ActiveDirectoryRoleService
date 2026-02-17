"""Service for Active Directory Organizational Unit operations."""
import logging

from django.conf import settings
from ldap3 import LEVEL

from .base_service import BaseLDAPService

logger = logging.getLogger(__name__)

OU_ATTRIBUTES = [
    'ou',
    'distinguishedName',
    'description',
    'whenCreated',
    'whenChanged',
]


class OUService(BaseLDAPService):
    """Operations on AD Organizational Unit objects."""

    def get_tree(self, base_dn=None):
        """Build OU tree from base DN, returns nested dict structure."""
        base = base_dn or settings.AD_BASE_DN
        ous = self.search(base, '(objectClass=organizationalUnit)',
                          OU_ATTRIBUTES)

        # Build parent -> children mapping
        nodes = {}
        for ou in ous:
            dn = ou['dn']
            nodes[dn] = {
                'dn': dn,
                'attributes': ou['attributes'],
                'name': ou['attributes'].get('ou', dn.split(',')[0]),
                'children': [],
            }

        # Build tree by matching parent DNs
        roots = []
        for dn, node in nodes.items():
            parent_dn = ','.join(dn.split(',')[1:])
            if parent_dn in nodes:
                nodes[parent_dn]['children'].append(node)
            else:
                roots.append(node)

        return {
            'dn': base,
            'name': base,
            'children': roots,
        }

    def get_children(self, parent_dn):
        """Get direct child OUs of a parent OU (for lazy loading)."""
        ous = self.search(parent_dn, '(objectClass=organizationalUnit)',
                          OU_ATTRIBUTES, scope=LEVEL)
        return ous

    def get_ou(self, dn):
        """Get OU details."""
        return self.get(dn, OU_ATTRIBUTES + ['*'])

    def get_ou_objects(self, dn):
        """Get all objects within an OU (users, computers, groups)."""
        users = self.search(
            dn,
            '(&(objectCategory=person)(objectClass=user))',
            ['sAMAccountName', 'displayName', 'distinguishedName',
             'userAccountControl'],
            scope=LEVEL,
        )
        computers = self.search(
            dn,
            '(objectClass=computer)',
            ['cn', 'dNSHostName', 'distinguishedName'],
            scope=LEVEL,
        )
        groups = self.search(
            dn,
            '(objectClass=group)',
            ['cn', 'description', 'distinguishedName', 'groupType'],
            scope=LEVEL,
        )
        return {
            'users': users,
            'computers': computers,
            'groups': groups,
        }
