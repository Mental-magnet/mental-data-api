FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install build dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --locked --no-install-project --no-editable

COPY src ./src

# Install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --locked --no-editable

FROM python:3.13-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PATH="/app/.venv/bin:${PATH}"

COPY --from=builder /app/.venv /app/.venv
COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "src.main:APP", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
