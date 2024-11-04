FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app
# Move the findingmodelforge directory from the tmp_packages directory to /findingmodelforge
RUN mv /app/tmp_packages/findingmodelforge /findingmodelforge

WORKDIR /app
# Run uv sync, using the local packages directory for the findingmodelforge package
RUN uv sync --frozen --no-cache 

EXPOSE 80
CMD ["/app/.venv/bin/fastapi", "run", "--port", "80", "--host", "0.0.0.0"]