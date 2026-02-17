"""View mixins for role-based access control."""
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(AccessMixin):
    """Mixin that requires the user to have one of the specified roles.

    Usage:
        class MyView(RoleRequiredMixin, TemplateView):
            required_roles = ['Admin', 'HelpDesk']
    """
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        try:
            profile = request.user.userprofile
        except Exception:
            raise PermissionDenied

        user_roles = set(profile.roles.values_list('name', flat=True))
        if not user_roles.intersection(set(self.required_roles)):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
