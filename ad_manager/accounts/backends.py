"""Active Directory LDAP authentication backend."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

import ldap3
from ldap3.core.exceptions import LDAPException

from accounts.models import Role, UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class ADLDAPBackend(ModelBackend):
    """Authenticate users against Active Directory via LDAP."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            # Step 1: search for user with service account
            user_dn, ad_attrs = self._search_user(username)
            if user_dn is None:
                return None

            # Step 2: bind as the user to verify password
            if not self._bind_as_user(user_dn, password):
                return None

            # Step 3: create or update Django user
            user = self._get_or_create_user(username, ad_attrs)

            # Step 4: create or update UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.ad_dn = user_dn
            profile.ad_guid = ad_attrs.get('objectGUID', '')
            profile.save()

            # Step 5: sync roles
            ad_groups = ad_attrs.get('memberOf', [])
            if isinstance(ad_groups, str):
                ad_groups = [ad_groups]
            self._sync_roles(profile, ad_groups)

            return user

        except LDAPException:
            logger.exception("LDAP error during authentication for %s", username)
            return None
        except Exception:
            logger.exception("Unexpected error during authentication for %s", username)
            return None

    def _search_user(self, username):
        """Search AD for user by sAMAccountName using the service account."""
        server_pool = ldap3.ServerPool(
            [ldap3.Server(uri, get_info=ldap3.NONE) for uri in settings.AD_LDAP_SERVERS],
            ldap3.ROUND_ROBIN,
        )
        conn = ldap3.Connection(
            server_pool,
            user=settings.AD_BIND_DN,
            password=settings.AD_BIND_PASSWORD,
            client_strategy=ldap3.SAFE_SYNC,
            auto_bind=True,
            read_only=True,
        )

        try:
            search_filter = f'(sAMAccountName={ldap3.utils.conv.escape_filter_chars(username)})'
            status, result, response, _ = conn.search(
                search_base=settings.AD_USER_SEARCH_BASE,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=[
                    'distinguishedName', 'givenName', 'sn', 'mail',
                    'objectGUID', 'memberOf', 'sAMAccountName',
                ],
            )

            if not response:
                return None, {}

            entry = response[0]
            attrs = entry.get('attributes', {})
            dn = entry.get('dn', '')

            return dn, {
                'givenName': self._get_attr(attrs, 'givenName'),
                'sn': self._get_attr(attrs, 'sn'),
                'mail': self._get_attr(attrs, 'mail'),
                'objectGUID': self._get_attr(attrs, 'objectGUID'),
                'memberOf': attrs.get('memberOf', []),
            }
        finally:
            conn.unbind()

    def _bind_as_user(self, user_dn, password):
        """Attempt to bind with user DN and password to verify credentials."""
        server_pool = ldap3.ServerPool(
            [ldap3.Server(uri, get_info=ldap3.NONE) for uri in settings.AD_LDAP_SERVERS],
            ldap3.ROUND_ROBIN,
        )
        try:
            conn = ldap3.Connection(
                server_pool,
                user=user_dn,
                password=password,
                client_strategy=ldap3.SAFE_SYNC,
                auto_bind=True,
            )
            conn.unbind()
            return True
        except LDAPException:
            return False

    def _get_or_create_user(self, username, ad_attrs):
        """Create or update the Django User from AD attributes."""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': ad_attrs.get('givenName', ''),
                'last_name': ad_attrs.get('sn', ''),
                'email': ad_attrs.get('mail', ''),
            },
        )
        if not created:
            user.first_name = ad_attrs.get('givenName', '')
            user.last_name = ad_attrs.get('sn', '')
            user.email = ad_attrs.get('mail', '')
            user.save()
        return user

    def _sync_roles(self, user_profile, ad_groups):
        """Map AD group memberships to local Role objects."""
        matching_roles = Role.objects.filter(
            ad_group_dn__in=ad_groups,
        ).exclude(ad_group_dn='')
        user_profile.roles.set(matching_roles)

    @staticmethod
    def _get_attr(attrs, name):
        """Safely get a single-valued attribute from LDAP results."""
        val = attrs.get(name, '')
        if isinstance(val, list):
            return val[0] if val else ''
        return str(val) if val else ''
