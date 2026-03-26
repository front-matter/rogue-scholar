FROM python:3.14-trixie AS builder
LABEL maintainer="Front Matter <info@front-matter.de>"
LABEL org.opencontainers.image.source="https://github.com/front-matter/rogue-scholar"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="Rogue Scholar"
LABEL org.opencontainers.image.description="Rogue Scholar is a science blog archive based on the InvenioRDM repository software."

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    VIRTUAL_ENV=/opt/invenio/.venv \
    UV_PROJECT_ENVIRONMENT=/opt/invenio/.venv \
    PATH="/opt/invenio/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance

# Install OS package dependencies and Node.js in a single layer
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update --fix-missing && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y build-essential libssl-dev libffi-dev \
    python3-dev cargo pkg-config \
    libcairo2-dev libpango1.0-dev libgdk-pixbuf-xlib-2.0-dev \
    libxml2-dev libxslt1-dev libpq-dev libjpeg-dev \
    libwebp-dev libtiff-dev libcurl4-openssl-dev nodejs \
    --no-install-recommends && \
    npm install -g pnpm@latest-10

# Install uv and activate virtualenv
COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /uvx /bin/
RUN uv venv /opt/invenio/.venv

WORKDIR /opt/invenio

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . .

# Install Python dependencies (use --no-editable so the project is installed as
# a proper wheel
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Copy application files we need for Javascript compilation to instance path
COPY assets ${INVENIO_INSTANCE_PATH}/assets
COPY static ${INVENIO_INSTANCE_PATH}/static
COPY translations ${INVENIO_INSTANCE_PATH}/translations

# Compile translation catalogs
RUN pybabel compile -d ${INVENIO_INSTANCE_PATH}/translations

# Build Javascript assets into the instance path expected at runtime.
ENV WEBPACKEXT_PROJECT=invenio_assets.webpack:rspack_project
RUN --mount=type=cache,target=/var/cache/assets \
    invenio collect --verbose && \
    invenio webpack buildall


FROM python:3.14-slim-trixie AS runtime

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    VIRTUAL_ENV=/opt/invenio/.venv \
    PATH="/opt/invenio/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance

# create non-root invenio user
RUN adduser invenio --uid 1000 --gid 0 --no-create-home --disabled-password

# Install OS package dependencies
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update --fix-missing && \
    apt-get install -y apt-utils gpg libcairo2 debian-keyring \
    debian-archive-keyring apt-transport-https curl --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and compiled files from builder stage
COPY --from=builder --chown=1000:0 ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=builder --chown=1000:0 ${INVENIO_INSTANCE_PATH}/assets ${INVENIO_INSTANCE_PATH}/assets
COPY --from=builder --chown=1000:0 ${INVENIO_INSTANCE_PATH}/static ${INVENIO_INSTANCE_PATH}/static
COPY --from=builder --chown=1000:0 ${INVENIO_INSTANCE_PATH}/translations ${INVENIO_INSTANCE_PATH}/translations

# Copy files needed at runtime
COPY --chown=1000:0 app_data ${INVENIO_INSTANCE_PATH}/app_data
COPY --chown=1000:0 site ${INVENIO_INSTANCE_PATH}/site
COPY --chown=1000:0 templates ${INVENIO_INSTANCE_PATH}/templates
COPY --chown=1000:0 ./invenio.cfg ${INVENIO_INSTANCE_PATH}/invenio.cfg

# Prepare Gunicorn and Metrics
COPY --chown=1000:0 ./gunicorn.conf.py ${INVENIO_INSTANCE_PATH}/
RUN mkdir -p /tmp/prometheus_multiproc && chown 1000:0 /tmp/prometheus_multiproc

# Copy scripts used at runtime
COPY --chown=1000:0 --chmod=755 ./scripts ${INVENIO_INSTANCE_PATH}/scripts/

# Copy entrypoint script and set permissions
COPY --chown=1000:0 --chmod=755 ./entrypoint.sh /opt/invenio/.venv/bin/entrypoint.sh

WORKDIR /opt/invenio/src
USER invenio
EXPOSE 4000
CMD ["gunicorn", "invenio_app.wsgi:application", "--bind", "0.0.0.0:4000", "--workers", "2", "--threads", "4", "--config", "/opt/invenio/var/instance/gunicorn.conf.py"]
