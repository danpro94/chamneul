# Pinned runtime so local/CI/prod all run the same Python (model.md §1.2 drift-0).
FROM python:3.13-slim

# Bring the uv binary in from its official image (no curl install step needed).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies FIRST, using only the lockfiles, so this layer is cached
# and re-runs only when dependencies change — not on every source edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Then copy the source (changes here don't bust the dependency layer above).
COPY . .

EXPOSE 8000

# Dev server for the local MVP. Swap to gunicorn when moving toward prod.
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
