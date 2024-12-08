FROM findingmodelforge-files AS findingmodelforge
FROM python:3.12-slim

RUN apt-get update && apt-get install -y bash curl && curl -1sLf \
  'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash \
  && apt-get update && apt-get install -y infisical
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=findingmodelforge /findingmodelforge /findingmodelforge
COPY . /app

WORKDIR /app
# Run uv sync, using the local packages directory for the findingmodelforge package
RUN uv sync --frozen --no-cache 

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--workers", "1",  "--port", "8000", "--host", "0.0.0.0"]