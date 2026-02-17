"""Notification forms."""
from django import forms

from core.password import PASSWORD_MIN_LENGTH, validate_password
from notifications.models import NotificationConfig, EmailTemplate


class NotificationConfigForm(forms.ModelForm):
    """Form for editing the singleton notification configuration."""

    class Meta:
        model = NotificationConfig
        fields = [
            'backend_type',
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls',
            'ses_region', 'ses_access_key_id', 'ses_secret_access_key',
            'from_email', 'warn_days', 'enabled',
        ]
        widgets = {
            'smtp_password': forms.PasswordInput(render_value=True),
            'ses_secret_access_key': forms.PasswordInput(render_value=True),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'smtp_username': forms.TextInput(attrs={'class': 'form-control'}),
            'ses_region': forms.TextInput(attrs={'class': 'form-control'}),
            'ses_access_key_id': forms.TextInput(attrs={'class': 'form-control'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'warn_days': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EmailTemplateForm(forms.ModelForm):
    """Form for editing email templates."""

    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'body_html', 'body_text', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body_html': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 15,
            }),
            'body_text': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 8,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }


class SendEmailForm(forms.Form):
    """Form for composing and sending ad-hoc emails."""

    RECIPIENT_TYPE_CHOICES = [
        ('emails', 'Specific email addresses'),
        ('group', 'All members of an AD group'),
    ]

    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='emails',
    )
    recipient_emails = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter email addresses, one per line',
        }),
        help_text='One email address per line.',
    )
    group_dn = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )
    group_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for a group...',
        }),
    )
    use_template = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    template_id = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select a template --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email subject',
        }),
    )
    body_html = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 12,
            'placeholder': 'HTML email body. Supports Django template variables: {{ domain }}, etc.',
        }),
    )
    body_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 6,
            'placeholder': 'Plain text fallback (optional)',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        rtype = cleaned_data.get('recipient_type')

        if rtype == 'emails':
            raw = cleaned_data.get('recipient_emails', '').strip()
            if not raw:
                raise forms.ValidationError('Please enter at least one email address.')
            emails = [e.strip() for e in raw.splitlines() if e.strip()]
            for email in emails:
                if '@' not in email:
                    raise forms.ValidationError(f'Invalid email address: {email}')
            cleaned_data['parsed_emails'] = emails
        elif rtype == 'group':
            if not cleaned_data.get('group_dn'):
                raise forms.ValidationError('Please select an AD group.')

        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    """Form for requesting a password reset link."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True,
        })
    )


class PasswordResetForm(forms.Form):
    """Form for setting a new password."""

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
        }),
        min_length=PASSWORD_MIN_LENGTH,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        }),
        min_length=PASSWORD_MIN_LENGTH,
    )

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('new_password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        if pw:
            errors = validate_password(pw)
            if errors:
                raise forms.ValidationError(errors)
        return cleaned_data
