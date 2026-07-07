FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for GitPython
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY backend/ ./backend/
COPY cli/ ./cli/

# Install dependencies
RUN uv sync --frozen --no-dev

# Create repositories directory
RUN mkdir -p /app/repositories

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]