"""Template context processors for AD Manager."""
from django.conf import settings

from core.constants import ROLE_ADMIN, ROLE_HELPDESK, ROLE_GROUP_MANAGER, ROLE_READONLY, ROLE_HIERARCHY


def ad_context(request):
    """Inject AD domain and base DN into every template context."""
    return {
        'AD_DOMAIN': settings.AD_DOMAIN,
        'AD_BASE_DN': settings.AD_BASE_DN,
    }


def role_context(request):
    """Inject user role information into every template context."""
    ctx = {
        'user_highest_role': None,
        'user_roles': [],
        'is_admin': False,
        'is_helpdesk': False,
        'is_group_manager': False,
        'is_readonly': False,
    }

    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return ctx

    try:
        profile = request.user.userprofile
    except Exception:
        return ctx

    roles = list(profile.roles.values_list('name', flat=True))
    ctx['user_roles'] = roles

    # Determine highest role by priority
    highest = None
    highest_priority = -1
    for role_name in roles:
        priority = ROLE_HIERARCHY.get(role_name, -1)
        if priority > highest_priority:
            highest_priority = priority
            highest = role_name
    ctx['user_highest_role'] = highest

    # Permission booleans
    ctx['is_admin'] = ROLE_ADMIN in roles
    ctx['is_helpdesk'] = ROLE_HELPDESK in roles or ctx['is_admin']
    ctx['is_group_manager'] = ROLE_GROUP_MANAGER in roles or ctx['is_admin']
    ctx['is_readonly'] = ROLE_READONLY in roles or len(roles) > 0

    return ctx
