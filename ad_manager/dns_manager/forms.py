"""Forms for DNS record management."""
from django import forms

from core.constants import DNS_RECORD_TYPES


class DNSRecordForm(forms.Form):
    """Form for creating or editing a DNS record."""

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Record name (e.g. www)',
        }),
    )
    record_type = forms.ChoiceField(
        choices=[(t, t) for t in DNS_RECORD_TYPES],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_record_type'}),
    )
    data = forms.CharField(
        max_length=1024,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Record data',
        }),
        help_text='For MX: "priority hostname". For SRV: "priority weight port target".',
    )
    ttl = forms.IntegerField(
        initial=3600,
        min_value=0,
        max_value=2147483647,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    priority = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Priority (MX/SRV only)',
        }),
        help_text='Used for MX and SRV records only.',
    )
