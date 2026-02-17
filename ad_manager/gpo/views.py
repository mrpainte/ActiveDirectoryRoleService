"""Views for Group Policy Object management."""
import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from core.constants import ROLE_ADMIN, ROLE_HELPDESK, ROLE_READONLY
from core.mixins import RoleRequiredMixin
from directory.services.base_service import LDAPServiceError, dn_to_base64, base64_to_dn
from gpo.services.gpo_service import GPOService

logger = logging.getLogger(__name__)


class GPOListView(RoleRequiredMixin, View):
    """List all GPOs. ReadOnly+ access."""

    required_roles = [ROLE_READONLY, ROLE_HELPDESK, ROLE_ADMIN]

    def get(self, request):
        service = GPOService()
        try:
            gpos = service.list_gpos()
            for gpo in gpos:
                gpo['encoded_dn'] = dn_to_base64(gpo['dn'])
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to list GPOs: {exc}")
            gpos = []
        return render(request, 'gpo/gpo_list.html', {'gpos': gpos})


class GPODetailView(RoleRequiredMixin, View):
    """GPO detail with linked OUs."""

    required_roles = [ROLE_READONLY, ROLE_HELPDESK, ROLE_ADMIN]

    def get(self, request, encoded_dn):
        service = GPOService()
        dn = base64_to_dn(encoded_dn)
        try:
            gpo = service.get_gpo(dn)
            if not gpo:
                messages.error(request, "GPO not found.")
                return redirect('gpo:gpo_list')
            linked_ous = service.get_linked_ous(dn)
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to load GPO: {exc}")
            return redirect('gpo:gpo_list')
        return render(request, 'gpo/gpo_detail.html', {
            'gpo': gpo,
            'linked_ous': linked_ous,
            'encoded_dn': encoded_dn,
        })
