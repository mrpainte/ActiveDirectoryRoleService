"""Views for AD computer objects."""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from directory.services import ComputerService, LDAPServiceError
from directory.services.base_service import base64_to_dn

logger = logging.getLogger(__name__)


class ComputerListView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/computer_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        svc = ComputerService()
        query = self.request.GET.get('q', '').strip()
        page = int(self.request.GET.get('page', 1))

        try:
            if query:
                entries = svc.search_computers(query)
                context['results'] = {
                    'entries': entries,
                    'total': len(entries),
                    'page': 1,
                    'num_pages': 1,
                }
            else:
                context['results'] = svc.list_computers(page=page)
        except LDAPServiceError as exc:
            logger.exception("Failed to list computers")
            messages.error(self.request, f"LDAP error: {exc}")
            context['results'] = {
                'entries': [], 'total': 0, 'page': 1, 'num_pages': 0,
            }

        context['query'] = query
        return context


class ComputerDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/computer_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dn = base64_to_dn(kwargs['encoded_dn'])
        svc = ComputerService()

        try:
            context['computer'] = svc.get_computer(dn)
        except LDAPServiceError as exc:
            logger.exception("Failed to get computer: %s", dn)
            messages.error(self.request, f"LDAP error: {exc}")
            context['computer'] = None

        context['encoded_dn'] = kwargs['encoded_dn']
        return context
