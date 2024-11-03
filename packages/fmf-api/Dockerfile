FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app
RUN mkdir -p /findingmodelforge/dist
COPY ../findingmodelforge/dist/* /findingmodelforge/dist

# WORKDIR /app
# RUN uv sync --frozen --no-cache

# CMD ["/app/.venv/bin/fastapi", "run", "--port", "80", "--host", "0.0.0.0"]