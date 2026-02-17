# Deployment Guide

This guide covers deploying the AD Manager application with Docker behind an external reverse proxy that terminates SSL.

## Architecture

```
User (HTTPS) --> External Reverse Proxy --> EC2 :80 --> nginx --> gunicorn :8000 --> Django
                  (SSL termination)                    (static files)
```

Docker Compose runs six services:

| Service | Role |
|---------|------|
| **web** | Django app served by Gunicorn on port 8000 |
| **nginx** | Serves static files and proxies requests to web |
| **celery-worker** | Async task execution (emails, password expiry checks) |
| **celery-beat** | Periodic task scheduler |
| **postgres** | PostgreSQL 16 database |
| **redis** | Message broker for Celery and rate limiting |

## Prerequisites

- Docker and Docker Compose (plugin or standalone)
- An external reverse proxy (ALB, Nginx, Caddy, etc.) terminating SSL
- Network connectivity from the EC2 instance to your Active Directory domain controllers

## 1. Environment Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

### Django Settings

```bash
DJANGO_SETTINGS_MODULE=ad_manager.settings.production
DJANGO_SECRET_KEY=<generate-a-random-secret-key>
ALLOWED_HOSTS=adrs.example.com
TZ=UTC
```

- **`DJANGO_SECRET_KEY`** -- Generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- **`ALLOWED_HOSTS`** -- Comma-separated hostnames. Must include your public domain.

### Reverse Proxy Settings

```bash
SECURE_SSL_REDIRECT=false
CSRF_TRUSTED_ORIGINS=https://adrs.example.com
```

- **`SECURE_SSL_REDIRECT`** -- Must be `false` when SSL is terminated by an external proxy. If set to `true`, Django will create an infinite redirect loop.
- **`CSRF_TRUSTED_ORIGINS`** -- Must include the full origin (with `https://`) that users access. Without this, all form submissions (login, password resets, etc.) will fail with a 403 CSRF error. Comma-separated for multiple origins.

### Database

```bash
DB_NAME=ad_manager
DB_USER=ad_manager
DB_PASSWORD=<strong-password>
DB_HOST=postgres
DB_PORT=5432
```

- **`DB_HOST`** -- Keep as `postgres` when using the bundled PostgreSQL container. Only change if using an external database (e.g., RDS).
- **`DB_PASSWORD`** -- Used by both Django and the PostgreSQL container. Change from the default.

### Active Directory / LDAP

```bash
AD_LDAP_SERVERS=ldap://dc1.example.com,ldap://dc2.example.com
AD_LDAP_USE_SSL=false
AD_BASE_DN=DC=example,DC=com
AD_DOMAIN=EXAMPLE
AD_USER_SEARCH_BASE=DC=example,DC=com
AD_GROUP_SEARCH_BASE=DC=example,DC=com
AD_COMPUTER_SEARCH_BASE=DC=example,DC=com
AD_BIND_DN=CN=svc_admanager,OU=Service Accounts,DC=example,DC=com
AD_BIND_PASSWORD=<service-account-password>
```

- **`AD_LDAP_SERVERS`** -- Comma-separated list of domain controller URIs. Use `ldaps://` with `AD_LDAP_USE_SSL=true` for LDAPS.
- **`AD_BIND_DN`** / **`AD_BIND_PASSWORD`** -- Service account used for LDAP searches. Needs read access to users, groups, computers, OUs, DNS, and GPOs. User authentication is performed via a separate bind with the user's own credentials.
- **`AD_*_SEARCH_BASE`** -- Can be scoped to specific OUs to limit search scope. Defaults to `AD_BASE_DN`.

### Kerberos SSO (Optional)

```bash
AD_KERBEROS_ENABLED=false
AD_KERBEROS_KEYTAB=/etc/krb5.keytab
AD_KERBEROS_SERVICE=HTTP
```

Only enable if you have a keytab configured for the service principal. Requires mounting the keytab into the web container.

### Celery / Redis

```bash
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

Keep as-is when using the bundled Redis container.

### Email Notifications

Choose one backend:

**SMTP:**
```bash
NOTIFICATION_BACKEND=smtp
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=noreply@example.com
```

**AWS SES:**
```bash
NOTIFICATION_BACKEND=ses
AWS_SES_REGION=us-east-1
AWS_SES_ACCESS_KEY_ID=<access-key>
AWS_SES_SECRET_ACCESS_KEY=<secret-key>
DEFAULT_FROM_EMAIL=noreply@example.com
```

### Rate Limiting

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://redis:6379/0
RATE_LIMIT_LOGIN_MAX=5
RATE_LIMIT_LOGIN_WINDOW=300
```

Limits login attempts to 5 per 300 seconds (5 minutes) per IP.

### Session

```bash
SESSION_COOKIE_AGE=28800
```

Session lifetime in seconds. Default is 28800 (8 hours). Sessions also expire on browser close.

## 2. Build and Deploy

```bash
# Build images
make docker-build

# Start all services (detached)
make docker-up

# Verify all containers are running
docker compose -f docker/docker-compose.yml ps

# Check logs
make docker-logs

# Seed default roles and email templates
docker compose -f docker/docker-compose.yml exec web python manage.py seed_roles
```

The web entrypoint automatically runs database migrations and collects static files on startup.

## 3. Role Configuration

The application uses role-based access control mapped to Active Directory groups. Users who log in without a matching role will see an empty interface and get 403 errors on most pages.

### Seed Roles

After the first deployment, create the default roles and email templates:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec web python manage.py seed_roles
```

This creates four roles with empty AD group mappings:

| Role | Priority | Default Access |
|------|----------|----------------|
| **Admin** | 3 | Full access: all views, user creation, DNS, GPOs, audit log, notifications, delegation |
| **HelpDesk** | 2 | Password resets, enable/disable/unlock users, GPO browsing, group management |
| **GroupManager** | 1 | Manage members of delegated groups |
| **ReadOnly** | 0 | Browse users, computers, OUs, groups, GPOs |

### Map Roles to AD Groups

Each role must be mapped to an AD group's Distinguished Name. When a user logs in, the application reads their `memberOf` attribute from AD and matches those DNs to determine which roles to assign.

Update each role's `ad_group_dn` via the Django shell:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec web python manage.py shell
```

```python
from accounts.models import Role

# Map each role to an AD group DN
Role.objects.filter(name='Admin').update(
    ad_group_dn='CN=ADRS-Admins,OU=Groups,DC=example,DC=com'
)
Role.objects.filter(name='HelpDesk').update(
    ad_group_dn='CN=ADRS-HelpDesk,OU=Groups,DC=example,DC=com'
)
Role.objects.filter(name='GroupManager').update(
    ad_group_dn='CN=ADRS-GroupManagers,OU=Groups,DC=example,DC=com'
)
# Tip: map ReadOnly to a broad group like Domain Users so all
# authenticated users can at least browse the directory
Role.objects.filter(name='ReadOnly').update(
    ad_group_dn='CN=Domain Users,CN=Users,DC=example,DC=com'
)
```

Replace the DNs above with the actual Distinguished Names of your AD groups. You can find them with:

```powershell
# PowerShell on a domain controller
Get-ADGroup -Identity "GroupName" | Select-Object DistinguishedName
```

### Verify Role Assignment

After mapping roles, log out and log back in (roles are synced on each login). Then confirm your roles were assigned:

```bash
docker compose --env-file .env -f docker/docker-compose.yml exec web python manage.py shell
```

```python
from django.contrib.auth.models import User
user = User.objects.get(username='your_username')
print(list(user.userprofile.roles.values_list('name', flat=True)))
# Expected output: ['Admin', 'ReadOnly'] (or whichever roles match your AD groups)
```

### Navigation Visibility by Role

| Nav Item | Visible To |
|----------|-----------|
| Dashboard, Users, Computers, OUs, Groups | All authenticated users |
| DNS, GPOs | Admin only |
| Audit Log | Admin only |
| Notifications | All (but config pages require Admin) |
| Password Reset / Enable / Disable / Unlock | Admin, HelpDesk |
| Create User | Admin only |
| Delegated Group Management | Admin |
| My Groups | Admin, HelpDesk, GroupManager |

## 4. Reverse Proxy Configuration

Your external reverse proxy must:

1. **Terminate SSL** and forward traffic to the EC2 instance on port 80
2. **Set `X-Forwarded-Proto: https`** -- Django uses this header to determine the original protocol. Without it, CSRF validation and secure cookie handling will break.
3. **Set `X-Forwarded-For`** -- Used for audit logging and rate limiting by client IP.
4. **Forward the `Host` header** -- Must match a value in `ALLOWED_HOSTS`.

### Example: Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name adrs.example.com;

    ssl_certificate     /etc/ssl/certs/adrs.example.com.pem;
    ssl_certificate_key /etc/ssl/private/adrs.example.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://<ec2-private-ip>:80;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}

server {
    listen 80;
    server_name adrs.example.com;
    return 301 https://$host$request_uri;
}
```

### Example: AWS ALB

When using an Application Load Balancer:

- Create an HTTPS (443) listener with your ACM certificate
- Forward to a target group pointing at the EC2 instance on port 80
- ALB automatically sets `X-Forwarded-Proto` and `X-Forwarded-For`

## 5. Post-Deployment Verification

```bash
# Check all services are healthy
docker compose -f docker/docker-compose.yml ps

# Verify web container logs show successful startup
docker compose -f docker/docker-compose.yml logs web

# Verify celery-beat started without database errors
docker compose -f docker/docker-compose.yml logs celery-beat

# Test connectivity from the proxy
curl -I http://<ec2-private-ip>:80
```

If everything is configured correctly, accessing `https://adrs.example.com` should show the login page.

## 6. Maintenance

```bash
# View logs
make docker-logs

# Restart all services
make docker-down && make docker-up

# Rebuild after code changes
make docker-build && make docker-down && make docker-up

# Run a management command
docker compose -f docker/docker-compose.yml exec web python manage.py <command>

# Access Django shell
docker compose -f docker/docker-compose.yml exec web python manage.py shell

# Database backup
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U ad_manager ad_manager > backup.sql
```

## 7. Data Persistence

The following Docker volumes persist data across container restarts:

| Volume | Contents |
|--------|----------|
| `postgres-data` | PostgreSQL database |
| `redis-data` | Redis data (rate limit counters, Celery broker) |
| `static-files` | Collected static assets served by nginx |

To fully reset: `docker compose -f docker/docker-compose.yml down -v` (destroys all data).
