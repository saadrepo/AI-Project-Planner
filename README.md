# AI Project Planner

AI Project Planner is a project management app built with Django.

ProjectPilot AI is a server-rendered Django foundation for a modular project management application. Step 1 provides the infrastructure, custom user model, health endpoint, admin, and local development services only.

## Technology stack

- Python 3.12+
- Django 5+
- PostgreSQL with Django ORM
- Django Templates and Tailwind CSS CDN
- Redis and Celery
- Docker Compose

No frontend JavaScript framework is used.

## Local installation

1. Create and activate a virtual environment.
2. Install development dependencies:

   ```powershell
   python -m pip install -r requirements/development.txt
   ```

3. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
4. Ensure PostgreSQL is running and update `DATABASE_URL` if needed.

## Environment setup

Required variables are documented in `.env.example`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `REDIS_URL`, OpenAI settings, and email settings. `.env` is ignored by Git.

## Docker setup

Copy `.env.example` to `.env`, then start the services:

```powershell
docker compose up --build
```

Services:

- `web`: Django development server at http://localhost:8000
- `db`: PostgreSQL 16 with persistent `postgres_data`
- `redis`: Redis 7 with persistent `redis_data`
- `worker`: Celery worker connected to Redis

## Database and migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

The default local fallback uses PostgreSQL at `localhost:5432`. SQLite is not configured.

## Create a superuser

```powershell
python manage.py createsuperuser
```

The custom user authenticates with email.

## Run the development server

```powershell
python manage.py runserver
```

Open `/` for the minimal base template, `/health/` for the JSON health check, and `/admin/` for Django Admin.

## Run Celery

With Redis available:

```powershell
celery -A config.celery.app worker --loglevel=info
```

A small `health_task` exists only to verify task discovery; no application jobs are implemented yet.

## Run tests and checks

```powershell
python manage.py check
pytest
ruff check .
```
