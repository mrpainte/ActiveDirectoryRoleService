"""Management command to seed default roles and email templates."""
from django.core.management.base import BaseCommand

from accounts.models import Role
from core.constants import ALL_ROLES, ROLE_HIERARCHY


DEFAULT_EMAIL_TEMPLATES = [
    {
        'name': 'password_expiry',
        'subject': 'Your password will expire in {{ days_until_expiry }} days',
        'body_html': '',
        'body_text': (
            'Hello {{ display_name }},\n\n'
            'Your Active Directory password will expire on {{ expiry_date }}.\n'
            'Please change your password before it expires.\n\n'
            'This is an automated message from the AD Manager system.'
        ),
        'description': (
            'Variables: display_name, username, email, days_until_expiry, '
            'expiry_date, domain'
        ),
    },
    {
        'name': 'password_reset',
        'subject': 'Password Reset Request',
        'body_html': '',
        'body_text': (
            'Hello {{ display_name }},\n\n'
            'A password reset was requested for your account.\n'
            'Click the link below to set a new password:\n\n'
            '{{ reset_link }}\n\n'
            'This link expires in 1 hour. If you did not request this, '
            'please ignore this email.'
        ),
        'description': 'Variables: display_name, email, reset_link, domain',
    },
    {
        'name': 'welcome',
        'subject': 'Welcome to {{ domain }} - Your Account Has Been Created',
        'body_html': '',
        'body_text': (
            'Hello {{ display_name }},\n\n'
            'Your Active Directory account has been created.\n\n'
            'Username: {{ username }}\n'
            'Temporary Password: {{ temporary_password }}\n'
            'Domain: {{ domain }}\n\n'
            'You will be required to change your password upon first login.\n'
            'Your new password must be at least 15 characters long and contain '
            'at least 1 uppercase letter, 1 lowercase letter, 1 number, and '
            '1 special character.\n\n'
            'If you have any questions, please contact your IT administrator.'
        ),
        'description': (
            'Variables: display_name, username, temporary_password, domain'
        ),
    },
]


class Command(BaseCommand):
    help = 'Create default roles and email templates if they do not exist.'

    def handle(self, *args, **options):
        # Seed roles
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding roles...'))
        for role_name in ALL_ROLES:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'ad_group_dn': '',
                    'description': f'{role_name} role',
                    'priority': ROLE_HIERARCHY.get(role_name, 0),
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created role: {role_name}'))
            else:
                self.stdout.write(f'  Role already exists: {role_name}')

        # Seed email templates
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding email templates...'))
        from notifications.models import EmailTemplate

        for tmpl_data in DEFAULT_EMAIL_TEMPLATES:
            # Load HTML body from file if it exists
            html_body = tmpl_data['body_html']
            try:
                from django.template.loader import render_to_string
                html_path = f'notifications/email/{tmpl_data["name"]}.html'
                html_body = render_to_string(html_path, {})
            except Exception:
                pass  # Use default empty or provided body

            tmpl, created = EmailTemplate.objects.get_or_create(
                name=tmpl_data['name'],
                defaults={
                    'subject': tmpl_data['subject'],
                    'body_html': html_body,
                    'body_text': tmpl_data['body_text'],
                    'description': tmpl_data['description'],
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  Created email template: {tmpl_data["name"]}')
                )
            else:
                self.stdout.write(f'  Email template already exists: {tmpl_data["name"]}')
