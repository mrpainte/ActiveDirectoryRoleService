"""Views for AD Organizational Unit browsing."""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from directory.services import OUService, LDAPServiceError
from directory.services.base_service import base64_to_dn

logger = logging.getLogger(__name__)


class OUTreeView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/ou_tree.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        svc = OUService()

        try:
            context['tree'] = svc.get_tree()
        except LDAPServiceError as exc:
            logger.exception("Failed to load OU tree")
            messages.error(self.request, f"LDAP error: {exc}")
            context['tree'] = None

        return context


class OUChildrenView(LoginRequiredMixin, TemplateView):
    """HTMX endpoint returning child OUs as partial HTML."""
    template_name = 'directory/partials/ou_children.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent_dn = base64_to_dn(kwargs['encoded_dn'])
        svc = OUService()

        try:
            context['children'] = svc.get_children(parent_dn)
        except LDAPServiceError as exc:
            logger.exception("Failed to load OU children: %s", parent_dn)
            context['children'] = []

        return context


class OUDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/ou_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dn = base64_to_dn(kwargs['encoded_dn'])
        svc = OUService()

        try:
            context['ou'] = svc.get_ou(dn)
            context['ou_objects'] = svc.get_ou_objects(dn)
        except LDAPServiceError as exc:
            logger.exception("Failed to get OU: %s", dn)
            messages.error(self.request, f"LDAP error: {exc}")
            context['ou'] = None
            context['ou_objects'] = {'users': [], 'computers': [], 'groups': []}

        context['encoded_dn'] = kwargs['encoded_dn']
        return context
