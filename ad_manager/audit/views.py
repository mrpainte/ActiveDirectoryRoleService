"""Audit log views."""
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin

from core.constants import ROLE_ADMIN, DEFAULT_PAGE_SIZE
from core.mixins import RoleRequiredMixin
from audit.models import AuditEntry, CATEGORY_CHOICES
from audit.exporters import export_csv, export_json


class AuditListView(RoleRequiredMixin, ListView):
    """Paginated, filterable list of audit entries."""

    required_roles = [ROLE_ADMIN]
    model = AuditEntry
    template_name = 'audit/audit_list.html'
    context_object_name = 'entries'
    paginate_by = DEFAULT_PAGE_SIZE

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.GET

        date_from = params.get('date_from')
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = params.get('date_to')
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        category = params.get('category')
        if category:
            qs = qs.filter(category=category)

        username = params.get('username')
        if username:
            qs = qs.filter(username__icontains=username)

        action = params.get('action')
        if action:
            qs = qs.filter(action__icontains=action)

        success = params.get('success')
        if success in ('true', 'false'):
            qs = qs.filter(success=(success == 'true'))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_choices'] = CATEGORY_CHOICES
        context['filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'category': self.request.GET.get('category', ''),
            'username': self.request.GET.get('username', ''),
            'action': self.request.GET.get('action', ''),
            'success': self.request.GET.get('success', ''),
        }
        return context


class AuditDetailView(RoleRequiredMixin, DetailView):
    """Detail view for a single audit entry."""

    required_roles = [ROLE_ADMIN]
    model = AuditEntry
    template_name = 'audit/audit_detail.html'
    context_object_name = 'entry'


class AuditExportView(RoleRequiredMixin, View):
    """Export audit entries as CSV or JSON."""

    required_roles = [ROLE_ADMIN]

    def get(self, request):
        qs = AuditEntry.objects.all()
        params = request.GET

        date_from = params.get('date_from')
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = params.get('date_to')
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        category = params.get('category')
        if category:
            qs = qs.filter(category=category)

        username = params.get('username')
        if username:
            qs = qs.filter(username__icontains=username)

        action = params.get('action')
        if action:
            qs = qs.filter(action__icontains=action)

        success = params.get('success')
        if success in ('true', 'false'):
            qs = qs.filter(success=(success == 'true'))

        fmt = params.get('format', 'csv')
        if fmt == 'json':
            return export_json(qs)
        return export_csv(qs)
