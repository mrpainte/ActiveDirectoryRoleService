"""Thread-safe LDAP connection pool singleton."""
import logging
import threading

from django.conf import settings
from ldap3 import (
    ALL,
    Connection,
    ROUND_ROBIN,
    SAFE_SYNC,
    Server,
    ServerPool,
)

logger = logging.getLogger(__name__)

_pool_instance = None
_pool_lock = threading.Lock()


class LDAPConnectionPool:
    """Singleton LDAP connection pool using ldap3 ServerPool."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            with _pool_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        servers = []
        for uri in settings.AD_LDAP_SERVERS:
            servers.append(
                Server(
                    uri.strip(),
                    use_ssl=settings.AD_LDAP_USE_SSL,
                    get_info=ALL,
                    connect_timeout=settings.AD_LDAP_CONNECT_TIMEOUT,
                )
            )
        self.server_pool = ServerPool(servers, ROUND_ROBIN, active=True)
        self._initialised = True
        logger.info(
            "LDAP connection pool initialised with %d server(s)", len(servers)
        )

    def get_connection(self):
        """Return a bound Connection using the service account."""
        conn = Connection(
            self.server_pool,
            user=settings.AD_BIND_DN,
            password=settings.AD_BIND_PASSWORD,
            client_strategy=SAFE_SYNC,
            auto_bind=True,
            receive_timeout=settings.AD_LDAP_RECEIVE_TIMEOUT,
        )
        return conn

    def get_user_connection(self, user_dn, password):
        """Return a Connection bound with the given user credentials."""
        conn = Connection(
            self.server_pool,
            user=user_dn,
            password=password,
            client_strategy=SAFE_SYNC,
            auto_bind=True,
            receive_timeout=settings.AD_LDAP_RECEIVE_TIMEOUT,
        )
        return conn


def get_connection_pool():
    """Return the singleton LDAPConnectionPool instance."""
    return LDAPConnectionPool()
