"""Views for AD user management."""
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, View

from core.constants import ROLE_ADMIN, ROLE_HELPDESK
from core.mixins import RoleRequiredMixin
from core.password import generate_password, validate_password
from directory.services import UserService, OUService, LDAPServiceError
from directory.services.base_service import base64_to_dn, dn_to_base64

logger = logging.getLogger(__name__)


class UserListView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/user_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        svc = UserService()
        query = self.request.GET.get('q', '').strip()
        page = int(self.request.GET.get('page', 1))

        try:
            if query:
                entries = svc.search_users(query)
                context['results'] = {
                    'entries': entries,
                    'total': len(entries),
                    'page': 1,
                    'num_pages': 1,
                }
            else:
                context['results'] = svc.list_users(page=page)
        except LDAPServiceError as exc:
            logger.exception("Failed to list users")
            messages.error(self.request, f"LDAP error: {exc}")
            context['results'] = {
                'entries': [], 'total': 0, 'page': 1, 'num_pages': 0,
            }

        context['query'] = query
        return context


class UserDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'directory/user_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dn = base64_to_dn(kwargs['encoded_dn'])
        svc = UserService()

        try:
            context['user_obj'] = svc.get_user(dn)
            context['user_groups'] = svc.get_user_groups(dn)
        except LDAPServiceError as exc:
            logger.exception("Failed to get user: %s", dn)
            messages.error(self.request, f"LDAP error: {exc}")
            context['user_obj'] = None
            context['user_groups'] = []

        context['encoded_dn'] = kwargs['encoded_dn']
        return context


class UserResetPasswordView(RoleRequiredMixin, View):
    required_roles = [ROLE_ADMIN, ROLE_HELPDESK]

    def post(self, request, encoded_dn):
        dn = base64_to_dn(encoded_dn)
        new_password = request.POST.get('new_password', '')
        if not new_password:
            messages.error(request, "Password cannot be empty.")
            return redirect('directory:user_detail', encoded_dn=encoded_dn)

        # Validate password complexity
        errors = validate_password(new_password)
        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect('directory:user_detail', encoded_dn=encoded_dn)

        svc = UserService()
        try:
            svc.reset_password(dn, new_password)
            messages.success(request, "Password reset successfully.")
        except LDAPServiceError as exc:
            logger.exception("Failed to reset password: %s", dn)
            messages.error(request, f"Password reset failed: {exc}")

        return redirect('directory:user_detail', encoded_dn=encoded_dn)


class UserToggleView(RoleRequiredMixin, View):
    required_roles = [ROLE_ADMIN, ROLE_HELPDESK]

    def post(self, request, encoded_dn):
        dn = base64_to_dn(encoded_dn)
        action = request.POST.get('action', 'disable')
        svc = UserService()

        try:
            if action == 'enable':
                svc.enable_user(dn)
                messages.success(request, "User account enabled.")
            else:
                svc.disable_user(dn)
                messages.success(request, "User account disabled.")
        except LDAPServiceError as exc:
            logger.exception("Failed to toggle user: %s", dn)
            messages.error(request, f"Operation failed: {exc}")

        return redirect('directory:user_detail', encoded_dn=encoded_dn)


class UserUnlockView(RoleRequiredMixin, View):
    required_roles = [ROLE_ADMIN, ROLE_HELPDESK]

    def post(self, request, encoded_dn):
        dn = base64_to_dn(encoded_dn)
        svc = UserService()

        try:
            svc.unlock_user(dn)
            messages.success(request, "User account unlocked.")
        except LDAPServiceError as exc:
            logger.exception("Failed to unlock user: %s", dn)
            messages.error(request, f"Unlock failed: {exc}")

        return redirect('directory:user_detail', encoded_dn=encoded_dn)


class GeneratePasswordView(RoleRequiredMixin, View):
    """AJAX endpoint that returns a generated password."""
    required_roles = [ROLE_ADMIN, ROLE_HELPDESK]

    def get(self, request):
        password = generate_password()
        return JsonResponse({'password': password})


class UserCreateView(RoleRequiredMixin, View):
    required_roles = [ROLE_ADMIN]
    template_name = 'directory/user_create.html'

    def _get_ou_choices(self):
        """Fetch OUs for the target OU dropdown."""
        ou_svc = OUService()
        try:
            from django.conf import settings
            ous = ou_svc.search(
                settings.AD_BASE_DN,
                '(objectClass=organizationalUnit)',
                ['distinguishedName', 'ou'],
            )
            choices = []
            for ou in ous:
                ou_name = ou['attributes'].get('ou', ou['dn'])
                if isinstance(ou_name, list):
                    ou_name = ou_name[0] if ou_name else ou['dn']
                choices.append((ou['dn'], ou_name))
            choices.sort(key=lambda c: c[1].lower())
            return choices
        except LDAPServiceError:
            logger.exception("Failed to fetch OUs for user creation")
            return []

    def get(self, request):
        ou_choices = self._get_ou_choices()
        return render(request, self.template_name, {'ou_choices': ou_choices})

    def post(self, request):
        ou_dn = request.POST.get('ou_dn', '').strip()
        sam_account_name = request.POST.get('sam_account_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        email = request.POST.get('email', '').strip()
        title = request.POST.get('title', '').strip()
        department = request.POST.get('department', '').strip()
        company = request.POST.get('company', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        description = request.POST.get('description', '').strip()
        enabled = request.POST.get('enabled') == 'on'
        send_welcome_email = request.POST.get('send_welcome_email') == 'on'

        # Validation
        errors = []
        if not ou_dn:
            errors.append("Target OU is required.")
        if not sam_account_name:
            errors.append("Username (sAMAccountName) is required.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not password:
            errors.append("Password is required.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        # Password complexity check
        if password and not errors:
            pw_errors = validate_password(password)
            errors.extend(pw_errors)

        if errors:
            for err in errors:
                messages.error(request, err)
            ou_choices = self._get_ou_choices()
            return render(request, self.template_name, {
                'ou_choices': ou_choices,
                'form_data': request.POST,
            })

        svc = UserService()
        try:
            user_dn = svc.create_user(
                ou_dn=ou_dn,
                sam_account_name=sam_account_name,
                first_name=first_name,
                last_name=last_name,
                password=password,
                email=email,
                title=title,
                department=department,
                company=company,
                telephone=telephone,
                description=description,
                enabled=enabled,
            )
            messages.success(request, f"User '{sam_account_name}' created successfully.")

            # Send welcome email if requested and email is provided
            if send_welcome_email and email:
                self._send_welcome_email(
                    email=email,
                    display_name=f"{first_name} {last_name}".strip(),
                    username=sam_account_name,
                    temporary_password=password,
                    user_dn=user_dn,
                )
                messages.info(request, f"Welcome email queued for {email}.")

            return redirect('directory:user_detail',
                            encoded_dn=dn_to_base64(user_dn))
        except LDAPServiceError as exc:
            logger.exception("Failed to create user: %s", sam_account_name)
            messages.error(request, f"User creation failed: {exc}")
            ou_choices = self._get_ou_choices()
            return render(request, self.template_name, {
                'ou_choices': ou_choices,
                'form_data': request.POST,
            })

    def _send_welcome_email(self, email, display_name, username,
                            temporary_password, user_dn):
        """Queue a welcome email for the newly created user."""
        try:
            from notifications.tasks import send_notification_email
            from django.conf import settings
            send_notification_email.delay(
                'welcome',
                email,
                {
                    'display_name': display_name,
                    'username': username,
                    'temporary_password': temporary_password,
                    'domain': settings.AD_DOMAIN,
                },
                user_dn,
            )
        except Exception:
            # Celery unavailable - try synchronous send
            try:
                from notifications.services.email_service import EmailService
                from django.conf import settings
                service = EmailService()
                service.send_template(
                    'welcome',
                    email,
                    {
                        'display_name': display_name,
                        'username': username,
                        'temporary_password': temporary_password,
                        'domain': settings.AD_DOMAIN,
                    },
                    user_dn,
                )
            except Exception:
                logger.exception("Failed to send welcome email to %s", email)
