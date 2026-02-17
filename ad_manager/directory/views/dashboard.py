"""Dashboard view showing domain summary statistics."""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from directory.services import UserService, ComputerService, LDAPServiceError

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_svc = UserService()
        computer_svc = ComputerService()

        try:
            users_result = user_svc.list_users(page_size=10000)
            context['total_users'] = users_result['total']
        except LDAPServiceError:
            logger.exception("Failed to count users")
            context['total_users'] = '?'
            context['ldap_error'] = True

        try:
            computers_result = computer_svc.list_computers(page_size=10000)
            context['total_computers'] = computers_result['total']

            # Domain controllers: server trust account flag (0x2000)
            dcs = [
                c for c in computers_result['entries']
                if int(c['attributes'].get('userAccountControl', 0)) & 0x2000
            ]
            context['domain_controllers'] = dcs
            context['total_dcs'] = len(dcs)
        except LDAPServiceError:
            logger.exception("Failed to count computers")
            context['total_computers'] = '?'
            context['domain_controllers'] = []
            context['total_dcs'] = '?'
            context['ldap_error'] = True

        try:
            from directory.services.base_service import BaseLDAPService
            from django.conf import settings
            svc = BaseLDAPService()
            groups = svc.search(
                settings.AD_GROUP_SEARCH_BASE,
                '(objectClass=group)',
                ['cn'],
            )
            context['total_groups'] = len(groups)
        except LDAPServiceError:
            logger.exception("Failed to count groups")
            context['total_groups'] = '?'
            context['ldap_error'] = True

        return context
