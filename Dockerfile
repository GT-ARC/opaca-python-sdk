FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.10-slim
COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY . .
RUN uv sync --no-install-project

ENTRYPOINT [ "uv", "run", "--no-project", "src/main.py" ]
