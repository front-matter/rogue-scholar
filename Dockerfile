FROM python:3.13.11-bookworm AS builder
LABEL maintainer="Front Matter <info@front-matter.de>"

# Dockerfile that builds the Rogue Scholar Docker image.

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en

# Install OS package dependencies and Node.js in a single layer
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update --fix-missing && \
    apt-get install -y build-essential libssl-dev libffi-dev \
    python3-dev cargo pkg-config curl --no-install-recommends && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs --no-install-recommends && \
    npm install -g pnpm@latest-10

# Install uv and activate virtualenv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
RUN uv venv /opt/invenio/.venv

# Use the virtual environment automatically
ENV VIRTUAL_ENV=/opt/invenio/.venv \
    UV_PROJECT_ENVIRONMENT=/opt/invenio/.venv \
    PATH="/opt/invenio/.venv/bin:$PATH" \
    WORKING_DIR=/opt/invenio \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance

WORKDIR ${WORKING_DIR}

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Build Javascript assets using rspack
ENV WEBPACKEXT_PROJECT=invenio_assets.webpack:rspack_project
RUN --mount=type=cache,target=/var/cache/assets \
    invenio collect --verbose && \
    invenio webpack create

# Copy application files to instance path
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}/
COPY site ${INVENIO_INSTANCE_PATH}/site
COPY static ${INVENIO_INSTANCE_PATH}/static
COPY assets ${INVENIO_INSTANCE_PATH}/assets
COPY templates ${INVENIO_INSTANCE_PATH}/templates
COPY app_data ${INVENIO_INSTANCE_PATH}/app_data
COPY translations ${INVENIO_INSTANCE_PATH}/translations

# Enable the option to have a deterministic javascript dependency build
# From: https://github.com/tu-graz-library/docker-invenio-base
COPY ./package.json ${INVENIO_INSTANCE_PATH}/assets/
COPY ./pnpm-lock.yaml ${INVENIO_INSTANCE_PATH}/assets/

WORKDIR ${INVENIO_INSTANCE_PATH}/assets
RUN pnpm install && \
    pnpm run build

# Gather runtime libraries into a single directory for easy copying
RUN ARCH=$(dpkg --print-architecture) && \
    LIB_DIR="/usr/lib/${ARCH}-linux-gnu" && \
    mkdir -p /invenio-libs && \
    cp -P ${LIB_DIR}/libcairo*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libpango*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libharfbuzz*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libfontconfig*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libfreetype*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libpixman*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libpng*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libexpat*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libbrotli*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libxcb*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libX*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libfribidi*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libthai*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libglib*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libgobject*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libdatrie*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libpcre2*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libffi*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libbsd*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libmd*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libpq*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libssl*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libcrypto*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libxml2*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libxslt*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libexslt*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libjpeg*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libwebp*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libtiff*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libz*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/liblzma*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libcurl*.so* /invenio-libs/ && \
    cp -P ${LIB_DIR}/libnghttp*.so* /invenio-libs/ 2>/dev/null || true && \
    cp -P ${LIB_DIR}/librtmp*.so* /invenio-libs/ 2>/dev/null || true && \
    cp -P ${LIB_DIR}/libssh*.so* /invenio-libs/ 2>/dev/null || true && \
    cp -P ${LIB_DIR}/libicui18n*.so* /invenio-libs/ 2>/dev/null || true && \
    cp -P ${LIB_DIR}/libicuuc*.so* /invenio-libs/ 2>/dev/null || true && \
    cp -P ${LIB_DIR}/libicudata*.so* /invenio-libs/ 2>/dev/null || true

FROM python:3.13.11-slim-bookworm AS runtime

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en

ENV VIRTUAL_ENV=/opt/invenio/.venv \
    PATH="/opt/invenio/.venv/bin:$PATH" \
    WORKING_DIR=/opt/invenio \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance

# create non-root invenio user
ENV INVENIO_USER_ID=1654
RUN adduser invenio --uid ${INVENIO_USER_ID} --gid 0 --no-create-home --disabled-password

# Copy runtime libraries from builder (Cairo for invenio_formatter, etc.)
RUN ARCH=$(dpkg --print-architecture) && \
    mkdir -p /usr/lib/${ARCH}-linux-gnu
COPY --from=builder /invenio-libs/* /usr/lib/
RUN ARCH=$(dpkg --print-architecture) && \
    mv /usr/lib/*.so* /usr/lib/${ARCH}-linux-gnu/ 2>/dev/null || true

COPY --from=builder --chown=1654:0 ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/site ${INVENIO_INSTANCE_PATH}/site
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/static ${INVENIO_INSTANCE_PATH}/static
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/assets ${INVENIO_INSTANCE_PATH}/assets
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/templates ${INVENIO_INSTANCE_PATH}/templates
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/app_data ${INVENIO_INSTANCE_PATH}/app_data
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/translations ${INVENIO_INSTANCE_PATH}/translations
COPY --from=builder --chown=1654:0 ${INVENIO_INSTANCE_PATH}/invenio.cfg ${INVENIO_INSTANCE_PATH}/invenio.cfg
COPY --chown=1654:0 ./Caddyfile /etc/caddy/Caddyfile
COPY --chown=1654:0 --chmod=755 ./entrypoint.sh /opt/invenio/.venv/bin/entrypoint.sh

WORKDIR ${WORKING_DIR}/src

USER invenio
EXPOSE 4000
CMD ["gunicorn", "invenio_app.wsgi:application", "--bind", "0.0.0.0:4000", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "ERROR"]
