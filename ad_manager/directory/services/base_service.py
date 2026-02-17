"""Base LDAP service with common search/modify operations."""
import base64
import logging

from ldap3 import SUBTREE
from ldap3.core.exceptions import LDAPException

from .ldap_connection import get_connection_pool

logger = logging.getLogger(__name__)


def dn_to_base64(dn):
    """Encode a DN to URL-safe base64."""
    return base64.urlsafe_b64encode(dn.encode('utf-8')).decode('ascii')


def base64_to_dn(encoded):
    """Decode a URL-safe base64 string back to a DN."""
    return base64.urlsafe_b64decode(encoded.encode('ascii')).decode('utf-8')


class LDAPServiceError(Exception):
    """Wrapper for LDAP operation errors."""
    pass


class BaseLDAPService:
    """Base class providing common LDAP operations."""

    def __init__(self):
        self.pool = get_connection_pool()

    def search(self, base_dn, filter_str, attributes, scope=SUBTREE,
               page_size=1000):
        """Paged LDAP search returning a list of entry dicts."""
        conn = self.pool.get_connection()
        try:
            results = conn.extend.standard.paged_search(
                search_base=base_dn,
                search_filter=filter_str,
                search_scope=scope,
                attributes=attributes,
                paged_size=page_size,
                generator=False,
            )
            entries = []
            for entry in results:
                if entry.get('type') == 'searchResEntry':
                    entries.append({
                        'dn': entry['dn'],
                        'attributes': dict(entry['attributes']),
                    })
            return entries
        except LDAPException as exc:
            logger.exception("LDAP search failed: base=%s filter=%s",
                             base_dn, filter_str)
            raise LDAPServiceError(f"Search failed: {exc}") from exc
        finally:
            conn.unbind()

    def get(self, dn, attributes):
        """Get a single object by its DN."""
        conn = self.pool.get_connection()
        try:
            status, result, response, _ = conn.search(
                search_base=dn,
                search_filter='(objectClass=*)',
                search_scope='BASE',
                attributes=attributes,
            )
            if response:
                entry = response[0]
                return {
                    'dn': entry['dn'],
                    'attributes': dict(entry['attributes']),
                }
            return None
        except LDAPException as exc:
            logger.exception("LDAP get failed: dn=%s", dn)
            raise LDAPServiceError(f"Get failed: {exc}") from exc
        finally:
            conn.unbind()

    def modify(self, dn, changes):
        """Modify attributes on an LDAP object.

        ``changes`` should be a dict of {attribute: [(operation, [values])]}.
        """
        conn = self.pool.get_connection()
        try:
            status = conn.modify(dn, changes)
            if not status:
                raise LDAPServiceError(
                    f"Modify failed on {dn}: {conn.result}"
                )
            return True
        except LDAPException as exc:
            logger.exception("LDAP modify failed: dn=%s", dn)
            raise LDAPServiceError(f"Modify failed: {exc}") from exc
        finally:
            conn.unbind()

    def add(self, dn, object_class, attributes):
        """Create a new LDAP object.

        ``object_class`` can be a string or list of objectClass values.
        ``attributes`` is a dict of {attribute_name: value_or_list}.
        """
        conn = self.pool.get_connection()
        try:
            status = conn.add(dn, object_class, attributes)
            if not status:
                raise LDAPServiceError(
                    f"Add failed for {dn}: {conn.result}"
                )
            return True
        except LDAPException as exc:
            logger.exception("LDAP add failed: dn=%s", dn)
            raise LDAPServiceError(f"Add failed: {exc}") from exc
        finally:
            conn.unbind()

    def delete(self, dn):
        """Delete an LDAP object by DN."""
        conn = self.pool.get_connection()
        try:
            status = conn.delete(dn)
            if not status:
                raise LDAPServiceError(
                    f"Delete failed on {dn}: {conn.result}"
                )
            return True
        except LDAPException as exc:
            logger.exception("LDAP delete failed: dn=%s", dn)
            raise LDAPServiceError(f"Delete failed: {exc}") from exc
        finally:
            conn.unbind()
