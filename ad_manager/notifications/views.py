"""Notification views."""
import logging

from django.contrib import messages
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import Template, Context
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from core.constants import ROLE_ADMIN, DEFAULT_PAGE_SIZE
from core.mixins import RoleRequiredMixin
from notifications.forms import (
    EmailTemplateForm,
    NotificationConfigForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    SendEmailForm,
)
from notifications.models import (
    EmailTemplate,
    NotificationConfig,
    SentNotification,
)
from notifications.tasks import send_notification_email, send_bulk_email

logger = logging.getLogger(__name__)

PASSWORD_RESET_MAX_AGE = 3600  # 1 hour


class NotificationConfigView(RoleRequiredMixin, View):
    """Admin-only notification configuration form."""

    required_roles = [ROLE_ADMIN]
    template_name = 'notifications/config.html'

    def get(self, request):
        config = NotificationConfig.get_config()
        form = NotificationConfigForm(instance=config)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        config = NotificationConfig.get_config()
        form = NotificationConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification configuration saved.')
            return redirect('notifications:config')
        return render(request, self.template_name, {'form': form})


class EmailTemplateListView(RoleRequiredMixin, ListView):
    """Admin-only list of email templates."""

    required_roles = [ROLE_ADMIN]
    model = EmailTemplate
    template_name = 'notifications/template_list.html'
    context_object_name = 'templates'


class EmailTemplateEditView(RoleRequiredMixin, View):
    """Admin-only edit view for email templates."""

    required_roles = [ROLE_ADMIN]
    template_name = 'notifications/template_edit.html'

    def get(self, request, pk):
        tmpl = get_object_or_404(EmailTemplate, pk=pk)
        form = EmailTemplateForm(instance=tmpl)
        return render(request, self.template_name, {'form': form, 'email_template': tmpl})

    def post(self, request, pk):
        tmpl = get_object_or_404(EmailTemplate, pk=pk)
        form = EmailTemplateForm(request.POST, instance=tmpl)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email template updated.')
            return redirect('notifications:template_list')
        return render(request, self.template_name, {'form': form, 'email_template': tmpl})


class EmailTemplatePreviewView(RoleRequiredMixin, View):
    """HTMX endpoint that renders a template with user-supplied test data."""

    required_roles = [ROLE_ADMIN]

    def get(self, request, pk):
        """Return the test form with auto-detected variables and sample values."""
        tmpl = get_object_or_404(EmailTemplate, pk=pk)
        variables = _extract_template_variables(tmpl)
        return render(request, 'notifications/template_preview.html', {
            'email_template': tmpl,
            'variables': variables,
            'rendered_html': None,
            'rendered_subject': None,
        })

    def post(self, request, pk):
        """Render the template with user-supplied variable values."""
        tmpl = get_object_or_404(EmailTemplate, pk=pk)
        variables = _extract_template_variables(tmpl)

        # Build context from posted values, and attach current value to each var
        user_context = {}
        for var in variables:
            val = request.POST.get(f'var_{var["name"]}', var['sample'])
            user_context[var['name']] = val
            var['current_value'] = val

        try:
            rendered_subject = Template(tmpl.subject).render(Context(user_context))
            rendered_html = Template(tmpl.body_html).render(Context(user_context))
        except Exception as exc:
            rendered_subject = f'[Render error: {exc}]'
            rendered_html = f'<p class="text-danger">Template render error: {exc}</p>'

        return render(request, 'notifications/template_preview.html', {
            'email_template': tmpl,
            'variables': variables,
            'rendered_html': rendered_html,
            'rendered_subject': rendered_subject,
        })


class EmailTemplateSendTestView(RoleRequiredMixin, View):
    """Send a test email to a single address using user-supplied variable values."""

    required_roles = [ROLE_ADMIN]

    def post(self, request, pk):
        tmpl = get_object_or_404(EmailTemplate, pk=pk)
        test_email = request.POST.get('test_email', '').strip()
        if not test_email or '@' not in test_email:
            messages.error(request, 'Please enter a valid email address.')
            return redirect('notifications:template_preview', pk=pk)

        variables = _extract_template_variables(tmpl)
        user_context = {}
        for var in variables:
            user_context[var['name']] = request.POST.get(
                f'var_{var["name"]}', var['sample']
            )

        try:
            rendered_subject = Template(tmpl.subject).render(Context(user_context))
            rendered_html = Template(tmpl.body_html).render(Context(user_context))
            rendered_text = Template(tmpl.body_text).render(Context(user_context))
        except Exception as exc:
            messages.error(request, f'Template render error: {exc}')
            return redirect('notifications:template_preview', pk=pk)

        from notifications.services.email_service import EmailService
        service = EmailService()
        result = service.send_raw(
            test_email, rendered_subject, rendered_html, rendered_text,
            metadata={'test_send': True, 'template': tmpl.name,
                      'sent_by': request.user.username},
        )

        if result and result.status == 'sent':
            messages.success(request, f'Test email sent to {test_email}.')
        else:
            error_msg = result.error_message if result else 'Unknown error'
            messages.error(request, f'Test email failed: {error_msg}')

        return redirect('notifications:template_preview', pk=pk)


# Well-known variables with sample values, grouped by usage
_KNOWN_VARIABLES = {
    'display_name': 'John Doe',
    'username': 'jdoe',
    'email': 'jdoe@example.com',
    'domain': 'EXAMPLE',
    'base_dn': 'DC=example,DC=com',
    'days_until_expiry': '7',
    'expiry_date': 'March 15, 2026',
    'reset_link': 'https://admanager.example.com/notifications/password-reset/abc123/',
    'temporary_password': 'T3mp!Pass_Ex@mple',
    'group_name': 'IT-Admins',
    'group_dn': 'CN=IT-Admins,OU=Groups,DC=example,DC=com',
}


def _extract_template_variables(tmpl):
    """Extract {{ variable }} references from a template's subject, HTML, and text bodies.

    Returns a list of dicts: [{'name': 'var_name', 'sample': 'sample value'}, ...]
    """
    import re
    combined = f"{tmpl.subject}\n{tmpl.body_html}\n{tmpl.body_text}"
    # Match {{ var_name }} and {{ var_name|filter }}
    matches = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)', combined)
    # Deduplicate preserving order
    seen = set()
    variables = []
    for name in matches:
        if name not in seen:
            seen.add(name)
            variables.append({
                'name': name,
                'sample': _KNOWN_VARIABLES.get(name, f'sample_{name}'),
            })
    return variables


class SentNotificationListView(RoleRequiredMixin, ListView):
    """Admin-only log of sent notifications."""

    required_roles = [ROLE_ADMIN]
    model = SentNotification
    template_name = 'notifications/history.html'
    context_object_name = 'notifications'
    paginate_by = DEFAULT_PAGE_SIZE

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.GET

        date_from = params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        status = params.get('status')
        if status:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'status': self.request.GET.get('status', ''),
        }
        context['status_choices'] = SentNotification.STATUS_CHOICES
        return context


class EmailTemplateCreateView(RoleRequiredMixin, View):
    """Admin-only view to create a new email template."""

    required_roles = [ROLE_ADMIN]
    template_name = 'notifications/template_create.html'

    def get(self, request):
        form = EmailTemplateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email template created.')
            return redirect('notifications:template_list')
        return render(request, self.template_name, {'form': form})


class SendEmailView(RoleRequiredMixin, View):
    """Admin-only view to compose and send ad-hoc emails."""

    required_roles = [ROLE_ADMIN]
    template_name = 'notifications/send_email.html'

    def get(self, request):
        form = SendEmailForm()
        # If a template_id is provided via query param, pre-fill the form
        template_id = request.GET.get('template_id')
        if template_id:
            try:
                tmpl = EmailTemplate.objects.get(pk=template_id, is_active=True)
                form = SendEmailForm(initial={
                    'use_template': True,
                    'template_id': tmpl.pk,
                    'subject': tmpl.subject,
                    'body_html': tmpl.body_html,
                    'body_text': tmpl.body_text,
                })
            except EmailTemplate.DoesNotExist:
                pass
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SendEmailForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        subject = form.cleaned_data['subject']
        body_html = form.cleaned_data['body_html']
        body_text = form.cleaned_data.get('body_text', '')
        recipient_type = form.cleaned_data['recipient_type']

        # Resolve recipient emails
        if recipient_type == 'emails':
            recipient_emails = form.cleaned_data['parsed_emails']
        elif recipient_type == 'group':
            group_dn = form.cleaned_data['group_dn']
            recipient_emails = self._resolve_group_emails(group_dn)
            if not recipient_emails:
                messages.error(
                    request,
                    'No members with email addresses found in that group.'
                )
                return render(request, self.template_name, {'form': form})

        # Render any Django template variables in subject/body
        from django.conf import settings
        tmpl_context = Context({
            'domain': settings.AD_DOMAIN,
            'base_dn': settings.AD_BASE_DN,
        })
        rendered_subject = Template(subject).render(tmpl_context)
        rendered_html = Template(body_html).render(tmpl_context)
        rendered_text = Template(body_text).render(tmpl_context) if body_text else ''

        # Queue the bulk send
        try:
            send_bulk_email.delay(
                rendered_subject,
                rendered_html,
                rendered_text,
                recipient_emails,
                metadata={'sent_by': request.user.username},
            )
            messages.success(
                request,
                f'Email queued for {len(recipient_emails)} recipient(s). '
                f'Check the send history for delivery status.'
            )
        except Exception:
            # Celery unavailable - send synchronously
            from notifications.services.email_service import EmailService
            service = EmailService()
            for email in recipient_emails:
                service.send_raw(
                    email, rendered_subject, rendered_html, rendered_text,
                    metadata={'sent_by': request.user.username},
                )
            messages.success(
                request,
                f'Email sent to {len(recipient_emails)} recipient(s).'
            )

        return redirect('notifications:history')

    def _resolve_group_emails(self, group_dn):
        """Resolve AD group members to their email addresses."""
        try:
            from groups.services.group_service import GroupService
            from directory.services import UserService

            group_svc = GroupService()
            user_svc = UserService()
            members = group_svc.get_members(group_dn)

            emails = []
            for member in members:
                member_dn = member.get('dn', '') if isinstance(member, dict) else member
                if not member_dn:
                    continue
                try:
                    user = user_svc.get_user(member_dn)
                    if user:
                        email = user['attributes'].get('mail', '')
                        if email:
                            emails.append(email)
                except Exception:
                    continue
            return emails
        except Exception:
            logger.exception("Failed to resolve group members for %s", group_dn)
            return []


class GroupSearchView(RoleRequiredMixin, View):
    """AJAX endpoint: search AD groups by name for the send-email group picker."""

    required_roles = [ROLE_ADMIN]

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse({'results': []})

        try:
            from groups.services.group_service import GroupService
            svc = GroupService()
            groups = svc.search_groups(query)
            results = [
                {
                    'dn': g['dn'],
                    'name': g['attributes'].get('cn', g['dn']),
                    'description': g['attributes'].get('description', ''),
                }
                for g in groups[:20]
            ]
            return JsonResponse({'results': results})
        except Exception:
            return JsonResponse({'results': []})


class PasswordResetRequestView(View):
    """Public view: user enters email to receive a password reset token."""

    template_name = 'notifications/password_reset_request.html'

    def get(self, request):
        form = PasswordResetRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Generate a signed token
            signer = signing.TimestampSigner()
            token = signer.sign(email)

            # Queue the reset email
            reset_link = request.build_absolute_uri(
                f'/notifications/password-reset/{token}/'
            )

            try:
                send_notification_email.delay(
                    'password_reset',
                    email,
                    {
                        'email': email,
                        'reset_link': reset_link,
                        'display_name': email.split('@')[0],
                    },
                )
            except Exception:
                # If Celery is down, try synchronously
                from notifications.services.email_service import EmailService
                service = EmailService()
                service.send_template(
                    'password_reset',
                    email,
                    {
                        'email': email,
                        'reset_link': reset_link,
                        'display_name': email.split('@')[0],
                    },
                )

            # Always show success (don't reveal whether email exists)
            return render(request, 'notifications/password_reset_sent.html')

        return render(request, self.template_name, {'form': form})


class PasswordResetConfirmView(View):
    """Public view: user enters new password with a valid token."""

    template_name = 'notifications/password_reset_confirm.html'

    def _verify_token(self, token):
        """Verify the signed token and return the email, or None."""
        try:
            signer = signing.TimestampSigner()
            email = signer.unsign(token, max_age=PASSWORD_RESET_MAX_AGE)
            return email
        except (signing.BadSignature, signing.SignatureExpired):
            return None

    def get(self, request, token):
        email = self._verify_token(token)
        if email is None:
            messages.error(request, 'This password reset link is invalid or has expired.')
            return redirect('notifications:password_reset_request')

        form = PasswordResetForm()
        return render(request, self.template_name, {'form': form, 'token': token})

    def post(self, request, token):
        email = self._verify_token(token)
        if email is None:
            messages.error(request, 'This password reset link is invalid or has expired.')
            return redirect('notifications:password_reset_request')

        form = PasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']

            try:
                from directory.services import UserService
                user_service = UserService()
                # Find the user by email and reset password
                users = user_service.search_users(email)
                if users:
                    user_dn = users[0].get('distinguishedName', '')
                    user_service.reset_password(user_dn, new_password)
                    messages.success(
                        request,
                        'Your password has been reset successfully. You can now log in.',
                    )
                    return redirect('accounts:login')
                else:
                    messages.error(request, 'User not found.')
            except Exception:
                logger.exception("Password reset failed for %s", email)
                messages.error(request, 'Password reset failed. Please try again or contact support.')

        return render(request, self.template_name, {'form': form, 'token': token})
