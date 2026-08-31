# One image: FastAPI serves the API and the built SPA from the same origin (ADR-0003).
# No secret is read at build time; runtime configuration arrives as environment variables.

# ---------- stage 1: build the web app ----------
FROM node:24-slim AS web

WORKDIR /app/web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

# ---------- stage 2: the runtime ----------
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.8.0 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ENV=production \
    PORT=8080

COPY pyproject.toml uv.lock ./
COPY core/ ./core/
COPY api/ ./api/
RUN uv sync --frozen --no-dev

COPY --from=web /app/web/dist ./web/dist

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
