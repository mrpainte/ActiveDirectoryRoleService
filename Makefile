.PHONY: help dev migrate shell collectstatic docker-up docker-down docker-build \
       dev-build dev-up dev-down dev-logs dev-seed dev-reset dev-ps dev-shell

# Detect docker compose command (plugin vs standalone)
DOCKER_COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev:  ## Run Django development server
	cd ad_manager && python manage.py runserver

migrate:  ## Run database migrations
	cd ad_manager && python manage.py migrate

makemigrations:  ## Create new migrations
	cd ad_manager && python manage.py makemigrations

shell:  ## Open Django shell
	cd ad_manager && python manage.py shell

collectstatic:  ## Collect static files
	cd ad_manager && python manage.py collectstatic --noinput

seed-roles:  ## Seed default roles
	cd ad_manager && python manage.py seed_roles

docker-build:  ## Build Docker images
	$(DOCKER_COMPOSE) --env-file .env -f docker/docker-compose.yml build

docker-up:  ## Start all services
	$(DOCKER_COMPOSE) --env-file .env -f docker/docker-compose.yml up -d

docker-down:  ## Stop all services
	$(DOCKER_COMPOSE) --env-file .env -f docker/docker-compose.yml down

docker-logs:  ## View logs
	$(DOCKER_COMPOSE) --env-file .env -f docker/docker-compose.yml logs -f

celery-worker:  ## Run Celery worker
	cd ad_manager && celery -A ad_manager worker -l info

celery-beat:  ## Run Celery beat scheduler
	cd ad_manager && celery -A ad_manager beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# ─── Local Dev with Samba AD DC ─────────────────────────────────────────────

DEV_COMPOSE = $(DOCKER_COMPOSE) --env-file .env.dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml

dev-build:  ## Build all images including Samba AD DC
	$(DEV_COMPOSE) build

dev-up:  ## Start all services with local Samba AD DC
	$(DEV_COMPOSE) up -d

dev-down:  ## Stop all dev services
	$(DEV_COMPOSE) down

dev-logs:  ## Tail logs for all dev services
	$(DEV_COMPOSE) logs -f

dev-ps:  ## Show status of dev services
	$(DEV_COMPOSE) ps

dev-shell:  ## Open Django shell in the web container
	$(DEV_COMPOSE) exec web python manage.py shell

dev-seed:  ## Seed Samba AD + Django roles for development
	@echo "=== Step 1/3: Seeding Samba AD directory ==="
	$(DEV_COMPOSE) exec samba-dc python3 /usr/local/bin/seed-directory.py --host ldap://localhost
	@echo ""
	@echo "=== Step 2/3: Seeding Django roles and email templates ==="
	$(DEV_COMPOSE) exec web python manage.py seed_roles
	@echo ""
	@echo "=== Step 3/3: Mapping roles to DEV.LOCAL AD groups ==="
	$(DEV_COMPOSE) exec web python manage.py shell -c "\
from accounts.models import Role; \
role_map = { \
    'Admin': 'CN=ADRS-Admins,OU=Groups,DC=dev,DC=local', \
    'HelpDesk': 'CN=ADRS-HelpDesk,OU=Groups,DC=dev,DC=local', \
    'GroupManager': 'CN=ADRS-GroupManagers,OU=Groups,DC=dev,DC=local', \
}; \
[print(f'  Mapped {r.name} -> {dn}') or setattr(r, 'ad_group_dn', dn) or r.save() for r in Role.objects.all() if (dn := role_map.get(r.name))];\
print('  ReadOnly role has no AD group mapping (by design)');\
"
	@echo ""
	@echo "=== Dev seed complete ==="
	@echo "Login at http://localhost:8000 with:"
	@echo "  admin.user    / TestP@ssw0rd!2024  (Admin)"
	@echo "  helpdesk.user / TestP@ssw0rd!2024  (HelpDesk)"
	@echo "  groupmgr.user / TestP@ssw0rd!2024  (GroupManager)"
	@echo "  readonly.user / TestP@ssw0rd!2024  (no role)"
	@echo "  normal.user   / TestP@ssw0rd!2024  (no role)"

dev-reset:  ## Full teardown and reset (removes all data)
	$(DEV_COMPOSE) down -v
	$(DEV_COMPOSE) up -d
	@echo "Waiting for services to be healthy..."
	@sleep 15
	$(MAKE) dev-seed
