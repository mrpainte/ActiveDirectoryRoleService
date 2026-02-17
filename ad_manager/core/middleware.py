"""Core middleware for role context, audit, and rate limiting."""
import logging

from django.conf import settings
from django.http import JsonResponse

from core.constants import ROLE_HIERARCHY

logger = logging.getLogger(__name__)


class RoleContextMiddleware:
    """Attach user roles and highest role to the request object."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_roles = []
        request.highest_role = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                profile = request.user.userprofile
                roles = list(profile.roles.values_list('name', flat=True))
                request.user_roles = roles

                highest = None
                highest_priority = -1
                for role_name in roles:
                    priority = ROLE_HIERARCHY.get(role_name, -1)
                    if priority > highest_priority:
                        highest_priority = priority
                        highest = role_name
                request.highest_role = highest
            except Exception:
                pass

        return self.get_response(request)


class AuditMiddleware:
    """Store client IP on the request for audit logging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            request.client_ip = forwarded_for.split(',')[0].strip()
        else:
            request.client_ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

        return self.get_response(request)


class RateLimitMiddleware:
    """Redis-backed rate limiting for the login endpoint."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    settings.RATE_LIMIT_REDIS_URL,
                    decode_responses=True,
                )
            except Exception:
                logger.warning("Could not connect to Redis for rate limiting")
                return None
        return self._redis

    def __call__(self, request):
        if not settings.RATE_LIMIT_ENABLED:
            return self.get_response(request)

        if request.path == settings.LOGIN_URL and request.method == 'POST':
            client_ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', ''))
            key = f"rate_limit:login:{client_ip}"

            r = self._get_redis()
            if r is not None:
                try:
                    current = r.get(key)
                    if current is not None and int(current) >= settings.RATE_LIMIT_LOGIN_MAX:
                        ttl = r.ttl(key)
                        return JsonResponse(
                            {
                                'error': 'Too many login attempts. Please try again later.',
                                'retry_after': ttl if ttl > 0 else settings.RATE_LIMIT_LOGIN_WINDOW,
                            },
                            status=429,
                        )

                    pipe = r.pipeline()
                    pipe.incr(key)
                    pipe.expire(key, settings.RATE_LIMIT_LOGIN_WINDOW)
                    pipe.execute()
                except Exception:
                    logger.exception("Rate limit Redis error")

        return self.get_response(request)
