# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 5.1 web application for managing on-prem Active Directory: user/computer/OU browsing, group management with delegation, DNS record management, GPO viewing, password expiry notifications, and self-service password resets. All authentication is against AD via LDAP.

## Commands

All commands run from the repo root. The Django project root is `ad_manager/`.

```bash
make dev                # Run dev server (manage.py runserver)
make migrate            # Run database migrations
make makemigrations     # Create new migrations
make seed-roles         # Seed default roles + email templates
make shell              # Django shell
make celery-worker      # Run Celery worker locally
make celery-beat        # Run Celery beat scheduler locally

# Docker
make docker-build       # Build all images
make docker-up          # Start all services (detached)
make docker-down        # Stop all services
make docker-logs        # Tail logs

# Direct Django commands (from ad_manager/ directory)
cd ad_manager && python manage.py runserver
cd ad_manager && python manage.py test <app_name>
cd ad_manager && python manage.py test <app_name>.tests.TestClassName.test_method_name
```

Settings: `DJANGO_SETTINGS_MODULE=ad_manager.settings.development` (default in manage.py).

## Code Style

- Black: line-length 120, target Python 3.11+
- isort: profile "black", Django-aware sections (FUTURE, STDLIB, THIRDPARTY, DJANGO, FIRSTPARTY, LOCALFOLDER)

## Architecture

### Service Layer Pattern (critical)

**Never call LDAP directly from views.** All AD operations go through service classes in `directory/services/`:

```
BaseLDAPService (base_service.py)
├── search(), get(), modify(), add(), delete()
├── dn_to_base64() / base64_to_dn()    ← DN encoding for URLs
└── LDAPServiceError                    ← all LDAP errors wrapped
    ├── UserService (user_service.py)
    ├── ComputerService (computer_service.py)
    ├── OUService (ou_service.py)
    ├── GroupService (groups/services/group_service.py)
    ├── DNSService (dns_manager/services/dns_service.py)
    └── GPOService (gpo/services/gpo_service.py)
```

`LDAPConnectionPool` in `ldap_connection.py` is a thread-safe singleton using `ServerPool` with `ROUND_ROBIN` and `SAFE_SYNC` strategy. It provides `get_connection()` (service account) and `get_user_connection(dn, password)` (user auth). Connections are unbound in `finally` blocks after each operation.

### DN Encoding

Distinguished Names contain `=`, `,`, spaces that break URL routing. Always encode with `dn_to_base64(dn)` for URLs and decode with `base64_to_dn(encoded)` in views. URL patterns use `<str:encoded_dn>`.

### Role-Based Access Control

Four roles mapped from AD groups to the `accounts.Role` model: **Admin** (3), **HelpDesk** (2), **GroupManager** (1), **ReadOnly** (0). Priority numbers define hierarchy.

- `RoleContextMiddleware` attaches `request.user_roles` and `request.highest_role`
- `RoleRequiredMixin` (core/mixins.py) gates views: set `required_roles = [ROLE_ADMIN, ROLE_HELPDESK]`
- Context processors inject `is_admin`, `is_helpdesk`, `is_group_manager`, `is_readonly` into all templates
- `ADLDAPBackend` syncs roles on every login by matching `memberOf` group DNs to `Role.ad_group_dn`

### Authentication Flow

`ADLDAPBackend.authenticate()` → search by sAMAccountName with service account → bind as user to verify password → create/update Django User + UserProfile → sync AD group memberships to Role assignments.

### Audit Logging

Use `AuditLogger.log_from_request(request, action, category, target_dn, detail)` for all write operations. Categories are constants in `core/constants.py` (AUDIT_CATEGORY_AUTH, _USER, _GROUP, _DNS, etc.). The `AuditMiddleware` provides `request.client_ip`.

### Email/Notification System

`EmailService` loads `NotificationConfig` (singleton, pk=1) and selects `SMTPBackend` or `SESBackend`. Email templates are Django template strings stored in the `EmailTemplate` model, rendered with `django.template.Template`. `send_template(name, email, context)` for template-based sends, `send_raw()` for ad-hoc. Celery tasks handle async sends and scheduled password expiry checks.

### Password Policy

Defined in `core/password.py`: minimum 15 characters, requires 1 uppercase, 1 lowercase, 1 digit, 1 special character. `validate_password()` returns error list, `generate_password()` creates compliant passwords. Enforced server-side in both admin password reset and self-service reset views.

### AD Password Setting

AD requires `unicodePwd` attribute as UTF-16-LE encoded password wrapped in double quotes:
```python
encoded_pw = ('"%s"' % new_password).encode('utf-16-le')
```

### User Creation Sequence

Must disable account first (UAC `NORMAL_ACCOUNT | ACCOUNTDISABLE`), set password via `unicodePwd`, then enable by clearing the disable flag. If password set fails, the created object is cleaned up.

## App Responsibilities

| App | Role |
|-----|------|
| `core` | Base template (Bootstrap 5 + htmx), middleware, mixins, constants, password utils |
| `accounts` | Role/UserProfile models, ADLDAPBackend, Kerberos middleware, login views, seed_roles command |
| `directory` | LDAP connection pool, all AD services, user/computer/OU views + dashboard, template filters |
| `groups` | Group CRUD, DelegatedGroup/GroupManagerAssignment models, self-service delegation |
| `dns_manager` | DNS zone/record CRUD via LDAP, binary dnsRecord encoding/decoding |
| `gpo` | Read-only GPO browsing, linked OU resolution |
| `notifications` | NotificationConfig singleton, EmailTemplate CRUD, SMTP/SES backends, Celery tasks, password reset flow |
| `audit` | Immutable AuditEntry model, AuditLogger service, CSV/JSON export |

## Configuration

All external config via environment variables (see `.env.example`). Key prefixes: `AD_*` (LDAP), `DB_*` (PostgreSQL), `CELERY_*` (Redis), `EMAIL_*`/`AWS_SES_*` (mail), `RATE_LIMIT_*` (throttling). Settings split: `base.py` (shared), `development.py` (debug, insecure cookies, console email), `production.py` (HSTS, SSL redirect, logging).

## Docker Services

`docker-compose.yml` runs 6 services: **web** (Gunicorn), **celery-worker**, **celery-beat** (DatabaseScheduler), **postgres** (16-alpine), **redis** (7-alpine), **nginx** (reverse proxy + static files). Production settings module is used in Docker (`ad_manager.settings.production`).
