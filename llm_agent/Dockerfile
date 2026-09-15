# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim-trixie
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.3

FROM ${UV_IMAGE} AS uv
FROM ${PYTHON_IMAGE} AS python-runtime

ENV FASTMCP_CHECK_FOR_UPDATES=off \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/venv \
    PATH=/venv/bin:$PATH

WORKDIR /app

FROM python-runtime AS dependencies
COPY --from=uv /uv /uvx /bin/
ENV UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PROJECT_ENVIRONMENT=/venv

COPY .python-version pyproject.toml README.md uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --frozen

FROM dependencies AS build
COPY llm_agent /app/llm_agent
RUN uv sync --no-dev --compile-bytecode --no-editable --frozen

FROM python-runtime AS prod
# Refresh scan-identified OS packages; build tooling stays in the builder.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini perl-base gzip libc-bin libc6 libpcre2-8-0 libsqlite3-0 \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip uninstall -y pip \
 && useradd -r -u 10001 appuser

COPY --from=build --chown=10001:10001 /venv /venv
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/health', timeout=2).close()"]

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["uvicorn", "llm_agent.demo_app:app", "--host", "0.0.0.0", "--port", "8080"]
