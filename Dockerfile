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

# Compile translation catalogs
RUN pybabel compile -d ${INVENIO_INSTANCE_PATH}/translations

# Enable the option to have a deterministic javascript dependency build
# From: https://github.com/tu-graz-library/docker-invenio-base
COPY ./package.json ${INVENIO_INSTANCE_PATH}/assets/
COPY ./pnpm-lock.yaml ${INVENIO_INSTANCE_PATH}/assets/

WORKDIR ${INVENIO_INSTANCE_PATH}/assets
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install && \
    pnpm run build

# Gather runtime libraries by finding .so files directly (most reliable).
# Uses cp -L to dereference symlinks so only real files are stored.
# ldconfig in the runtime stage will re-create symlinks and cache.
RUN MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)" && \
    LIB_DIR="/usr/lib/${MULTIARCH}" && \
    mkdir -p /invenio-libs && \
    echo "${MULTIARCH}" > /invenio-libs/.arch && \
    for pattern in \
    'libcairo.so*' \
    'libpango-1.0.so*' 'libpangocairo-1.0.so*' 'libpangoft2-1.0.so*' \
    'libgdk_pixbuf-2.0.so*' \
    'libgobject-2.0.so*' 'libglib-2.0.so*' 'libgio-2.0.so*' 'libgmodule-2.0.so*' \
    'libxml2.so*' 'libxslt.so*' 'libexslt.so*' \
    'libpq.so*' 'libjpeg.so*' 'libwebp.so*' 'libtiff.so*' 'libcurl.so*' \
    'libfribidi.so*' 'libharfbuzz.so*' 'libfontconfig.so*' 'libfreetype.so*' \
    'libpixman-1.so*' 'libpng16.so*' 'libexpat.so*' \
    'libbrotlicommon.so*' 'libbrotlidec.so*' \
    'libdatrie.so*' 'libthai.so*' 'libpcre2-8.so*' 'libffi.so*' \
    'libbsd.so*' 'libmd.so*' 'libdeflate.so*' 'libjbig.so*' \
    'libzstd.so*' 'liblerc.so*' 'libnghttp2.so*' 'libssh2.so*' \
    'libssl.so*' 'libcrypto.so*' \
    'libicudata.so*' 'libicui18n.so*' 'libicuuc.so*' \
    'libX11.so*' 'libXext.so*' 'libXrender.so*' \
    'libxcb.so*' 'libxcb-render.so*' 'libxcb-shm.so*' \
    'libXau.so*' 'libXdmcp.so*' \
    ; do \
    find "${LIB_DIR}" -maxdepth 1 -name "${pattern}" -exec cp -Ln {} /invenio-libs/ \; 2>/dev/null || true; \
    done && \
    ls /invenio-libs/libcairo.so* || { echo "FATAL: libcairo not found in ${LIB_DIR}"; find /usr -name 'libcairo*' 2>/dev/null; exit 1; } && \
    echo "Collected $(ls /invenio-libs/ | wc -l) library files"

FROM python:3.13.11-slim-bookworm AS runtime

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    VIRTUAL_ENV=/opt/invenio/.venv \
    PATH="/opt/invenio/.venv/bin:$PATH" \
    WORKING_DIR=/opt/invenio \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance

# create non-root invenio user
ENV INVENIO_USER_ID=1654
RUN adduser invenio --uid ${INVENIO_USER_ID} --gid 0 --no-create-home --disabled-password

# Copy prebuilt runtime libraries into arch-specific directory
# so ctypes.util.find_library() can locate them via ldconfig cache
COPY --from=builder /invenio-libs/ /tmp/invenio-libs/
RUN MULTIARCH="$(cat /tmp/invenio-libs/.arch)" && \
    TARGET="/usr/lib/${MULTIARCH}" && \
    mkdir -p "${TARGET}" && \
    find /tmp/invenio-libs -maxdepth 1 -name '*.so*' -exec cp {} "${TARGET}/" \; && \
    rm -rf /tmp/invenio-libs && \
    ldconfig && \
    ldconfig -p | grep -i cairo && \
    python3 -c "import ctypes.util; r=ctypes.util.find_library('cairo'); print(f'cairo: {r}'); assert r, 'libcairo not found'"

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
COPY --chown=1654:0 ./entrypoint.py /opt/invenio/.venv/bin/entrypoint.py

WORKDIR ${WORKING_DIR}/src

USER invenio
EXPOSE 4000
# ENTRYPOINT ["python", "/opt/invenio/.venv/bin/entrypoint.py"]
CMD ["sh", "-c", "gunicorn invenio_app.wsgi:application --bind 0.0.0.0:4000 --workers 2 --threads 4 --timeout 60 --access-logfile - --error-logfile - --log-level ${GUNICORN_LOG_LEVEL:-WARNING}"]
