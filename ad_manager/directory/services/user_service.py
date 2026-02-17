"""Service for Active Directory user operations."""
import logging

from django.conf import settings
from ldap3 import MODIFY_REPLACE

from core.constants import DEFAULT_PAGE_SIZE, UAC_FLAGS
from .base_service import BaseLDAPService, LDAPServiceError

logger = logging.getLogger(__name__)

USER_ATTRIBUTES = [
    'sAMAccountName',
    'displayName',
    'mail',
    'userAccountControl',
    'whenCreated',
    'lastLogonTimestamp',
    'pwdLastSet',
    'memberOf',
    'distinguishedName',
    'objectGUID',
    'givenName',
    'sn',
    'title',
    'department',
    'company',
    'telephoneNumber',
    'description',
    'lockoutTime',
]

# Flags
UAC_ACCOUNTDISABLE = 0x0002


class UserService(BaseLDAPService):
    """Operations on AD user objects."""

    def list_users(self, search_base=None, search_filter=None, page=1,
                   page_size=DEFAULT_PAGE_SIZE):
        """List AD users with pagination."""
        base = search_base or settings.AD_USER_SEARCH_BASE
        ldap_filter = search_filter or '(&(objectCategory=person)(objectClass=user))'
        all_entries = self.search(base, ldap_filter, USER_ATTRIBUTES)
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

    def get_user(self, dn):
        """Get a single user with all attributes."""
        return self.get(dn, ['*'])

    def search_users(self, query):
        """Search users by name, email, or sAMAccountName."""
        escaped = query.replace('\\', '\\5c').replace('*', '\\2a').replace(
            '(', '\\28').replace(')', '\\29').replace('\x00', '\\00')
        ldap_filter = (
            '(&(objectCategory=person)(objectClass=user)'
            '(|(sAMAccountName=*{q}*)(displayName=*{q}*)'
            '(mail=*{q}*)(givenName=*{q}*)(sn=*{q}*)))'
        ).format(q=escaped)
        base = settings.AD_USER_SEARCH_BASE
        return self.search(base, ldap_filter, USER_ATTRIBUTES)

    def reset_password(self, dn, new_password):
        """Reset a user's password using the unicodePwd attribute."""
        encoded_pw = ('"%s"' % new_password).encode('utf-16-le')
        changes = {'unicodePwd': [(MODIFY_REPLACE, [encoded_pw])]}
        return self.modify(dn, changes)

    def enable_user(self, dn):
        """Enable a user account by clearing the ACCOUNTDISABLE flag."""
        user = self.get(dn, ['userAccountControl'])
        if not user:
            raise LDAPServiceError(f"User not found: {dn}")
        uac = int(user['attributes'].get('userAccountControl', 0))
        new_uac = uac & ~UAC_ACCOUNTDISABLE
        return self.modify(dn, {
            'userAccountControl': [(MODIFY_REPLACE, [new_uac])]
        })

    def disable_user(self, dn):
        """Disable a user account by setting the ACCOUNTDISABLE flag."""
        user = self.get(dn, ['userAccountControl'])
        if not user:
            raise LDAPServiceError(f"User not found: {dn}")
        uac = int(user['attributes'].get('userAccountControl', 0))
        new_uac = uac | UAC_ACCOUNTDISABLE
        return self.modify(dn, {
            'userAccountControl': [(MODIFY_REPLACE, [new_uac])]
        })

    def unlock_user(self, dn):
        """Unlock a user account by clearing the lockoutTime attribute."""
        return self.modify(dn, {
            'lockoutTime': [(MODIFY_REPLACE, [0])]
        })

    def create_user(self, ou_dn, sam_account_name, first_name, last_name,
                    password, email='', title='', department='', company='',
                    telephone='', description='', enabled=True):
        """Create a new AD user in the specified OU.

        1. Creates the user object with standard attributes.
        2. Sets the initial password via unicodePwd.
        3. Optionally enables the account.
        """
        cn = f"{first_name} {last_name}".strip() or sam_account_name
        user_dn = f"CN={cn},{ou_dn}"
        display_name = cn

        # NORMAL_ACCOUNT + ACCOUNTDISABLE (must disable first to set password)
        initial_uac = 0x0200 | UAC_ACCOUNTDISABLE

        attributes = {
            'sAMAccountName': sam_account_name,
            'userPrincipalName': f"{sam_account_name}@{settings.AD_DOMAIN}",
            'givenName': first_name,
            'sn': last_name,
            'displayName': display_name,
            'userAccountControl': initial_uac,
        }

        # Add optional attributes
        if email:
            attributes['mail'] = email
        if title:
            attributes['title'] = title
        if department:
            attributes['department'] = department
        if company:
            attributes['company'] = company
        if telephone:
            attributes['telephoneNumber'] = telephone
        if description:
            attributes['description'] = description

        # Step 1: Create the user object
        self.add(user_dn, ['top', 'person', 'organizationalPerson', 'user'],
                 attributes)

        # Step 2: Set the password
        try:
            self.reset_password(user_dn, password)
        except LDAPServiceError:
            # Clean up the created user if password set fails
            logger.error("Password set failed for new user %s, removing object", user_dn)
            self.delete(user_dn)
            raise

        # Step 3: Enable if requested
        if enabled:
            try:
                self.enable_user(user_dn)
            except LDAPServiceError:
                logger.warning("Failed to enable new user %s", user_dn)
                raise

        return user_dn

    def get_user_groups(self, dn):
        """Return list of groups the user belongs to."""
        user = self.get(dn, ['memberOf'])
        if not user:
            return []
        member_of = user['attributes'].get('memberOf', [])
        if isinstance(member_of, str):
            member_of = [member_of]
        return member_of
