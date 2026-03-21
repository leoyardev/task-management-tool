# Task Management Tool

A production-grade REST API for managing tasks and projects, built with Python and FastAPI. Designed with **Hexagonal Architecture** (Ports & Adapters), full test coverage across four layers, and Docker support for both development and production environments.

---

## Table of Contents

- [Architecture](#architecture)
- [Domain Model](#domain-model)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Configuration](#configuration)
- [Design Decisions](#design-decisions)
- [Technology Stack](#technology-stack)

---

## Architecture

This project follows **Hexagonal Architecture** (also known as Ports & Adapters), keeping the domain and business logic completely isolated from infrastructure and framework concerns.

Each layer has a strict dependency rule — inner layers never know about outer layers:

- **Domain** — pure Python, zero external dependencies. Entities, events, exceptions, and port interfaces.
- **Application** — orchestrates domain entities. Depends only on domain ports (never on concrete adapters).
- **Adapters** — concrete implementations. FastAPI routers, SQLAlchemy repositories, console notifier.
- **Infrastructure** — SQLAlchemy engine and session factory setup.


## Domain Model

### Entities

**Project**

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Auto-generated |
| `title` | string | Required |
| `deadline` | datetime | Required |
| `completed` | bool | Defaults to false |
| `created_at` | datetime | Auto-managed |
| `updated_at` | datetime | Auto-managed |

**Task**

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Auto-generated |
| `title` | string | Required |
| `description` | string | Optional |
| `deadline` | datetime | Must not exceed project deadline |
| `completed` | bool | Defaults to false |
| `project_id` | UUID | Optional — nullable FK to projects |
| `project_deadline` | datetime | Transient — loaded from project on read |
| `created_at` | datetime | Auto-managed |
| `updated_at` | datetime | Auto-managed |

### Business Rules

| Rule | Where enforced |
|---|---|
| Task deadline must not exceed project deadline | `Task._validate_deadline()` |
| Project completes only when all tasks are done | `Project.mark_complete(open_task_count)` |
| Reopening a task reopens its completed project | `TaskService.complete_task()` |
| Auto-complete project when last task done | `TaskService` — configurable via env var |
| Project deadline cascades to tasks when tightened | `ProjectService._cascade_deadline()` |
| Cannot update a completed project's deadline without reopening | `Project.update()` |

### Domain Events

Events are emitted by entities, collected via `pull_events()`, and dispatched by services to `NotificationPort`:

| Event | Emitted when |
|---|---|
| `TaskCompleted` | A task is marked complete |
| `TaskReopened` | A completed task is reopened |
| `ProjectCompleted` | A project is marked complete |
| `ProjectDeadlineChanged` | Project deadline moves earlier |
| `DeadlineApproaching` | Task deadline is within 24 hours |

---

## API Endpoints

Base URL: `/api/v1`

Interactive documentation: `http://localhost:8000/docs`

ReDoc documentation: `http://localhost:8000/redoc`

Health check: `http://localhost:8000/health`

### Projects

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `POST` | `/projects` | 201 | Create a project |
| `GET` | `/projects` | 200 | List all projects |
| `GET` | `/projects/{id}` | 200 | Get a project by id |
| `PUT` | `/projects/{id}` | 200 | Update a project |
| `DELETE` | `/projects/{id}` | 204 | Delete a project |
| `PATCH` | `/projects/{id}/complete` | 200 | Mark a project as completed |
| `GET` | `/projects/{id}/tasks` | 200 | Get all tasks for a project |
| `POST` | `/projects/{id}/tasks/{task_id}/link` | 200 | Link a task to a project |
| `DELETE` | `/projects/{id}/tasks/{task_id}/unlink` | 200 | Unlink a task from a project |

### Tasks

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `POST` | `/tasks` | 201 | Create a task |
| `GET` | `/tasks` | 200 | List all tasks |
| `GET` | `/tasks/{id}` | 200 | Get a task by id |
| `PUT` | `/tasks/{id}` | 200 | Update a task |
| `DELETE` | `/tasks/{id}` | 204 | Delete a task |
| `PATCH` | `/tasks/{id}/complete` | 200 | Mark a task as completed |

### Query Filters — `GET /tasks`

| Parameter | Type | Description |
|---|---|---|
| `completed` | bool | Filter by completion status |
| `overdue` | bool | Filter overdue tasks only |
| `project_id` | UUID | Filter tasks belonging to a project |

Filters compose with AND — `?completed=false&project_id=abc` returns open tasks in that project.

### HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Resource created |
| `204` | Deleted — no body |
| `404` | Resource not found |
| `409` | Conflict — already completed, invalid operation |
| `422` | Validation error — missing fields, deadline violation, open tasks |

---

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Setup

```bash
git clone <repo-url>
cd task-management-tool
```
```

### Run in production mode

```bash
docker compose up
```

This runs the `migrate` service first (Alembic migrations), then starts the `app` service with Gunicorn + 4 Uvicorn workers.

Open `http://localhost:8000/docs` for the Swagger UI.

### Run in development mode

```bash
docker compose --profile dev up
```

```bash
uv run pytest
uv run alembic upgrade head
```

### Stop everything

```bash
docker compose down --remove-orphans

# also wipe the database volume
docker compose down --remove-orphans --volumes
```

---

## Running Tests

### Inside the dev container

```bash
docker compose --profile dev up -d
docker compose exec dev bash
```

Run the full suite:

```bash
uv run pytest
```


### Linting and formatting

```bash
uv run ruff check .           # lint check
uv run ruff check . --fix     # auto-fix lint issues
uv run ruff format .          # format code
uv run ruff check . --fix && uv run ruff format .  # fix everything
```

---

## Configuration

All settings are loaded from environment variables by `AppConfig`. Never read `os.environ` directly in domain or application layers.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/tasks.db` | SQLAlchemy database URL |
| `AUTO_COMPLETE_PROJECT` | `false` | Auto-complete project when last open task is completed. Set to `true` to enable. |

Set via `docker-compose.yml` environment section or your `.env` file.

---

## Design Decisions

### Hexagonal Architecture

The domain layer has zero external dependencies — no SQLAlchemy, no FastAPI, no Pydantic (except frozen event models). Business logic is testable without a database or web framework. The entire persistence layer can be swapped (SQLite → PostgreSQL) without touching a single domain file.

### Specification Pattern for Task Filtering

`TaskRepository` uses the Specification pattern for composable filtering:

```python
spec = OpenTaskSpec() & BelongsToProjectSpec(project_id)
tasks = task_repo.find_all(spec)
```

Specifications are pure domain objects defined in the port. The repository applies them in Python after loading. This keeps SQL simple and filtering logic in the domain where it belongs.

### Mappers as Anti-Corruption Layer

`ProjectMapper` and `TaskMapper` are the only places where `UUID ↔ str` conversion happens. Neither the domain entity nor the ORM model knows about the other's existence. `_ensure_utc()` in `mappers/utils.py` reattaches UTC timezone after every DB read because SQLite strips `tzinfo` on write.

### API Versioning

All endpoints live under `/api/v1/`. Adding `/api/v2/` later requires only new router and schema files — v1 routes are unaffected. Schemas live inside `v1/` because response shapes are part of the versioned contract.

### Gunicorn + Uvicorn Workers in Production

The `prod` Docker target runs Gunicorn with `UvicornWorker` — 4 worker processes for concurrency, access and error logs sent to stdout/stderr for Docker log collection. The `dev` target uses `sleep infinity` so developers start any process manually inside the container.

### Docker Compose Profiles

```bash
docker compose up               # runs migrate + app (prod, Gunicorn)
docker compose --profile dev up # runs migrate + dev (sleep infinity)
```

The `migrate` service always runs regardless of profile, ensuring migrations are applied before either environment starts.

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Web framework | FastAPI | Latest |
| ASGI server (dev) | Uvicorn | Latest |
| ASGI server (prod) | Gunicorn + UvicornWorker | Latest |
| ORM | SQLAlchemy | 2.0 |
| Database | SQLite | — |
| Migrations | Alembic | Latest |
| Data validation | Pydantic | v2 |
| Package manager | uv | Latest |
| Linting / formatting | Ruff | Latest |
| Testing | pytest + pytest-asyncio | Latest |
| Containerisation | Docker + Docker Compose | Latest |