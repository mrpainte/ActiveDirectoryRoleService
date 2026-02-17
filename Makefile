.PHONY: help dev migrate shell collectstatic docker-up docker-down docker-build

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
	docker compose -f docker/docker-compose.yml build

docker-up:  ## Start all services
	docker compose -f docker/docker-compose.yml up -d

docker-down:  ## Stop all services
	docker compose -f docker/docker-compose.yml down

docker-logs:  ## View logs
	docker compose -f docker/docker-compose.yml logs -f

celery-worker:  ## Run Celery worker
	cd ad_manager && celery -A ad_manager worker -l info

celery-beat:  ## Run Celery beat scheduler
	cd ad_manager && celery -A ad_manager beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
