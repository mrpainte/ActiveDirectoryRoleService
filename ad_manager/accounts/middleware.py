"""Kerberos/SPNEGO authentication middleware."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model, login

from accounts.models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class KerberosNegotiateMiddleware:
    """If AD_KERBEROS_ENABLED, negotiate SPNEGO auth from the Authorization header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.AD_KERBEROS_ENABLED:
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Negotiate '):
            return self.get_response(request)

        try:
            import gssapi

            token = auth_header[len('Negotiate '):].strip()
            import base64
            in_token = base64.b64decode(token)

            server_creds = gssapi.Credentials(
                usage='accept',
                name=gssapi.Name(
                    f'{settings.AD_KERBEROS_SERVICE}@{settings.AD_DOMAIN}',
                    name_type=gssapi.NameType.hostbased_service,
                ),
            )
            ctx = gssapi.SecurityContext(creds=server_creds, usage='accept')
            ctx.step(in_token)

            if ctx.complete:
                principal = str(ctx.initiator_name)
                # Extract username from principal (user@REALM -> user)
                username = principal.split('@')[0]

                user, _ = User.objects.get_or_create(username=username)
                UserProfile.objects.get_or_create(user=user)
                login(request, user, backend='accounts.backends.ADLDAPBackend')

        except ImportError:
            logger.debug("gssapi not installed; Kerberos SSO disabled")
        except Exception:
            logger.exception("Kerberos negotiation failed")

        return self.get_response(request)
