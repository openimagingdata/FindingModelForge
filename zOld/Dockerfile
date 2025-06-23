FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/openimagingdata/FindingModelForge

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run uv sync, using the local packages directory for the findingmodelforge package
RUN uv sync --frozen --no-cache 

EXPOSE 8000

CMD ["/app/run_app.sh"]