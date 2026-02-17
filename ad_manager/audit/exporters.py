"""Audit log export utilities."""
import csv
import json

from django.http import StreamingHttpResponse, JsonResponse


class _Echo:
    """Pseudo-buffer for streaming CSV writes."""

    def write(self, value):
        return value


def export_csv(queryset, filename='audit_export.csv'):
    """Stream a queryset of AuditEntry objects as a CSV download."""
    pseudo_buffer = _Echo()
    writer = csv.writer(pseudo_buffer)

    def rows():
        yield writer.writerow([
            'Timestamp', 'Username', 'Action', 'Category',
            'Target DN', 'Success', 'IP Address', 'Detail',
        ])
        for entry in queryset.iterator():
            yield writer.writerow([
                entry.timestamp.isoformat(),
                entry.username,
                entry.action,
                entry.get_category_display(),
                entry.target_dn,
                entry.success,
                entry.ip_address or '',
                json.dumps(entry.detail),
            ])

    response = StreamingHttpResponse(rows(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def export_json(queryset, filename='audit_export.json'):
    """Return a queryset of AuditEntry objects as a JSON download."""
    data = []
    for entry in queryset.iterator():
        data.append({
            'timestamp': entry.timestamp.isoformat(),
            'username': entry.username,
            'action': entry.action,
            'category': entry.category,
            'category_display': entry.get_category_display(),
            'target_dn': entry.target_dn,
            'success': entry.success,
            'ip_address': entry.ip_address,
            'detail': entry.detail,
        })

    response = JsonResponse(data, safe=False, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
