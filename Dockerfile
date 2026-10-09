FROM python:3.13-slim-bookworm AS builder

ENV POETRY_VERSION=2.5.1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Resolve the locked application dependencies in an isolated environment.
RUN python -m pip install "poetry==${POETRY_VERSION}" \
    && python -m venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml poetry.lock README.md ./
COPY src ./src

RUN poetry install --only main --no-root --no-interaction --no-ansi \
    && poetry build --format wheel \
    && pip install --no-deps dist/*.whl


FROM python:3.13-slim-bookworm AS primary

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/omnia

# python-magic needs both the libmagic shared library and its magic database.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libmagic1 libmagic-mgc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN groupadd --system omnia \
    && useradd --system --gid omnia --create-home --home-dir /home/omnia --shell /usr/sbin/nologin omnia

USER omnia
