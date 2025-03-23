FROM rust:slim AS rust
FROM ghcr.io/openimagingdata/findingmodelforge-files AS findingmodelforge
FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/openimagingdata/findingmodelforge

# Install minimal build dependencies needed for tantivy
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    gcc \
    libc6-dev \
    && curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash \
    && apt-get update && apt-get install -y infisical

# Copy Rust from the rust image
COPY --from=rust /usr/local/cargo /usr/local/cargo
COPY --from=rust /usr/local/rustup /usr/local/rustup

# Set Rust environment variables
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=findingmodelforge /findingmodelforge /findingmodelforge
COPY . /app

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run uv sync, using the local packages directory for the findingmodelforge package
RUN uv sync --frozen --no-cache 

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["/app/run_app_prod.sh"]