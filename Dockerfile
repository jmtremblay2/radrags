FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml ./
COPY src/radrags/_version.py src/radrags/_version.py
RUN uv sync --no-dev --no-install-project

# Copy source and install the project
COPY src/ src/
RUN uv sync --no-dev

# Default config location
COPY radrags.ini.example /etc/radrags/radrags.ini

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "radrags", "--config", "/etc/radrags/radrags.ini"]
