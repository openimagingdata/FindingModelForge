FROM ghcr.io/openimagingdata/findingmodelforge-files AS findingmodelforge
FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/openimagingdata/findingmodelforge

RUN apt-get update && apt-get install -y bash curl && curl -1sLf \
  'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash \
  && apt-get update && apt-get install -y infisical
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=findingmodelforge /findingmodelforge /findingmodelforge
COPY . /app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run uv sync, using the local packages directory for the findingmodelforge package
RUN uv sync --frozen --no-cache 

EXPOSE 8000
COPY ./run_app_prod.sh /usr/local/bin
CMD ["run_app_prod.sh"]