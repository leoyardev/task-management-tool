FROM ghcr.io/astral-sh/uv:0.6.6 AS uv

FROM python:3.12-slim-bookworm AS base

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

FROM base AS dev

COPY . .

RUN if [ -f pyproject.toml ]; then \
      uv sync --dev; \
    else \
      echo "No pyproject.toml found, skipping dependency installation."; \
    fi

EXPOSE 8000

CMD ["sleep", "infinity"]


FROM base AS prod

COPY . .

RUN if [ -f pyproject.toml ]; then \
      uv sync --no-dev; \
    else \
      echo "No pyproject.toml found, skipping dependency installation."; \
    fi

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]