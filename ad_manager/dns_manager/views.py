"""Views for DNS management."""
import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from core.constants import ROLE_ADMIN
from core.mixins import RoleRequiredMixin
from directory.services.base_service import LDAPServiceError, dn_to_base64, base64_to_dn
from dns_manager.forms import DNSRecordForm
from dns_manager.services.dns_service import DNSService

logger = logging.getLogger(__name__)


class ZoneListView(RoleRequiredMixin, View):
    """List DNS zones. Admin only."""

    required_roles = [ROLE_ADMIN]

    def get(self, request):
        service = DNSService()
        try:
            zones = service.list_zones()
            for zone in zones:
                zone['encoded_dn'] = dn_to_base64(zone['dn'])
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to list DNS zones: {exc}")
            zones = []
        return render(request, 'dns_manager/zone_list.html', {'zones': zones})


class RecordListView(RoleRequiredMixin, View):
    """List DNS records in a zone."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, encoded_dn):
        service = DNSService()
        zone_dn = base64_to_dn(encoded_dn)
        try:
            records_raw = service.list_records(zone_dn)
            records = []
            for entry in records_raw:
                dns_records = entry['attributes'].get('dnsRecord', [])
                if isinstance(dns_records, bytes):
                    dns_records = [dns_records]
                decoded = []
                for raw in dns_records:
                    if isinstance(raw, bytes):
                        rec = service._decode_dns_record(raw)
                        if rec:
                            decoded.append(rec)
                entry['decoded_records'] = decoded
                entry['encoded_dn'] = dn_to_base64(entry['dn'])
                records.append(entry)
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to list records: {exc}")
            records = []
        return render(request, 'dns_manager/record_list.html', {
            'records': records,
            'zone_dn': zone_dn,
            'encoded_zone_dn': encoded_dn,
        })


class RecordCreateView(RoleRequiredMixin, View):
    """Create a DNS record."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, encoded_dn):
        form = DNSRecordForm()
        zone_dn = base64_to_dn(encoded_dn)
        return render(request, 'dns_manager/record_form.html', {
            'form': form,
            'zone_dn': zone_dn,
            'encoded_zone_dn': encoded_dn,
            'is_edit': False,
        })

    def post(self, request, encoded_dn):
        form = DNSRecordForm(request.POST)
        zone_dn = base64_to_dn(encoded_dn)
        if form.is_valid():
            service = DNSService()
            try:
                service.create_record(
                    zone_dn=zone_dn,
                    name=form.cleaned_data['name'],
                    record_type=form.cleaned_data['record_type'],
                    data=form.cleaned_data['data'],
                    ttl=form.cleaned_data['ttl'],
                )
                messages.success(request, "DNS record created successfully.")
                return redirect('dns_manager:record_list', encoded_dn=encoded_dn)
            except LDAPServiceError as exc:
                messages.error(request, f"Failed to create record: {exc}")
        return render(request, 'dns_manager/record_form.html', {
            'form': form,
            'zone_dn': zone_dn,
            'encoded_zone_dn': encoded_dn,
            'is_edit': False,
        })


class RecordEditView(RoleRequiredMixin, View):
    """Edit a DNS record."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, encoded_dn):
        service = DNSService()
        dn = base64_to_dn(encoded_dn)
        try:
            record = service.get_record(dn)
            if not record:
                messages.error(request, "Record not found.")
                return redirect('dns_manager:zone_list')
            # Pre-fill form from existing record
            dns_records = record['attributes'].get('dnsRecord', [])
            if isinstance(dns_records, bytes):
                dns_records = [dns_records]
            initial = {'name': record['attributes'].get('dc', '')}
            if dns_records:
                decoded = service._decode_dns_record(dns_records[0])
                if decoded:
                    initial['record_type'] = decoded['type']
                    initial['data'] = decoded['data']
                    initial['ttl'] = decoded['ttl']
            form = DNSRecordForm(initial=initial)
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to load record: {exc}")
            return redirect('dns_manager:zone_list')
        return render(request, 'dns_manager/record_form.html', {
            'form': form,
            'encoded_dn': encoded_dn,
            'is_edit': True,
        })

    def post(self, request, encoded_dn):
        form = DNSRecordForm(request.POST)
        dn = base64_to_dn(encoded_dn)
        if form.is_valid():
            service = DNSService()
            try:
                service.update_record(
                    dn=dn,
                    record_type=form.cleaned_data['record_type'],
                    data=form.cleaned_data['data'],
                    ttl=form.cleaned_data['ttl'],
                )
                messages.success(request, "DNS record updated successfully.")
                # Navigate back to zone list since we don't have the zone DN directly
                return redirect('dns_manager:zone_list')
            except LDAPServiceError as exc:
                messages.error(request, f"Failed to update record: {exc}")
        return render(request, 'dns_manager/record_form.html', {
            'form': form,
            'encoded_dn': encoded_dn,
            'is_edit': True,
        })


class RecordDeleteView(RoleRequiredMixin, View):
    """Delete a DNS record (POST with confirmation)."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, encoded_dn):
        service = DNSService()
        dn = base64_to_dn(encoded_dn)
        try:
            record = service.get_record(dn)
            if not record:
                messages.error(request, "Record not found.")
                return redirect('dns_manager:zone_list')
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to load record: {exc}")
            return redirect('dns_manager:zone_list')
        return render(request, 'dns_manager/record_confirm_delete.html', {
            'record': record,
            'encoded_dn': encoded_dn,
        })

    def post(self, request, encoded_dn):
        service = DNSService()
        dn = base64_to_dn(encoded_dn)
        try:
            service.delete_record(dn)
            messages.success(request, "DNS record deleted successfully.")
        except LDAPServiceError as exc:
            messages.error(request, f"Failed to delete record: {exc}")
        return redirect('dns_manager:zone_list')
