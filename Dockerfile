FROM python:3.13.11-bookworm AS builder
LABEL maintainer="Front Matter <info@front-matter.de>"
LABEL org.opencontainers.image.source="https://github.com/front-matter/rogue-scholar"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="Rogue Scholar"
LABEL org.opencontainers.image.description="Rogue Scholar is a science blog archive based on the InvenioRDM repository software."

# Dockerfile that builds the Rogue Scholar Docker image.

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en

# Install OS package dependencies and Node.js in a single layer
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update --fix-missing && \
    apt-get install -y build-essential libssl-dev libffi-dev \
    python3-dev cargo pkg-config curl \
    libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev \
    libxml2-dev libxslt1-dev libpq-dev libjpeg-dev \
    libwebp-dev libtiff-dev libcurl4-openssl-dev \
    --no-install-recommends && \
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
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install && \
    pnpm run build

# Gather runtime libraries into a single directory for easy copying
RUN ARCH="$(dpkg --print-architecture)" && \
    LIB_DIR="/usr/lib/${ARCH}-linux-gnu" && \
    mkdir -p /invenio-libs && \
    for lib in cairo pango harfbuzz fontconfig freetype pixman png expat brotli \
    xcb X11 Xau Xdmcp Xext Xrender fribidi thai glib-2.0 gobject-2.0 \
    datrie pcre2-8 ffi bsd md pq ssl crypto xml2 xslt exslt \
    jpeg webp tiff z lzma curl nghttp2 rtmp ssh2 \
    icui18n icuuc icudata; do \
    find ${LIB_DIR} -name "lib${lib}*.so*" -exec cp -P {} /invenio-libs/ \; 2>/dev/null || true; \
    done

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
RUN ARCH="$(dpkg --print-architecture)" && \
    mkdir -p "/usr/lib/${ARCH}-linux-gnu"
COPY --from=builder /invenio-libs/* /usr/lib/
RUN ARCH="$(dpkg --print-architecture)" && \
    mv /usr/lib/*.so* "/usr/lib/${ARCH}-linux-gnu/" 2>/dev/null || true && \
    ldconfig

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
