import logging
import os

import structlog

# Hard-code the prometheus multiprocess directory so it is set before
# prometheus_client is imported (it reads the env var at import time).
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")


def configure_logging() -> None:
    """Configure structlog with JSON (prod) or console (dev) output."""
    log_level_name = os.environ.get(
        "INVENIO_LOGGING_CONSOLE_LEVEL", "INFO"
    ).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    debug_mode = os.environ.get("INVENIO_DEBUG", "false").lower() == "true"

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if debug_mode:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    # Suppress handled exceptions logged at DEBUG by invenio's resource layer
    # (e.g. LogoNotFoundError, which is a normal 404 — not an application error)
    logging.getLogger("invenio").setLevel(max(log_level, logging.INFO))
    # Gunicorn access logs are emitted at INFO — ensure they always flow through structlog
    logging.getLogger("gunicorn.access").setLevel(logging.INFO)
    # Suppress noisy but harmless urllib3 connection pool full warnings
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
    # Suppress third-party deprecation warnings (marshmallow, pyparsing, …)
    # unless running in debug mode; they are noise in production logs
    if not debug_mode:
        logging.getLogger("py.warnings").setLevel(logging.ERROR)


def on_starting(server):
    """Called once in the master process before workers fork."""
    configure_logging()


def post_fork(server, worker):
    """Called in each worker after forking — re-initialise structlog context."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(worker_pid=worker.pid)


def worker_exit(server, worker):
    """Called when a worker exits — clean up prometheus multiprocess files."""
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)


class StructlogGunicornLogger:
    def __init__(self, cfg):
        self.error_log = structlog.get_logger("gunicorn.error")
        self.access_log = structlog.get_logger("gunicorn.access")
        self.cfg = cfg

    def critical(self, msg, *args, **kwargs):
        self.error_log.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.error_log.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.error_log.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.error_log.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.error_log.debug(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.error_log.error(msg, *args, exc_info=True, **kwargs)

    def access(self, resp, req, environ, request_time):
        status = resp.status
        status_code = (
            int(status.split(None, 1)[0])
            if isinstance(status, str)
            else status
        )

        self.access_log.info(
            "request",
            method=environ.get("REQUEST_METHOD"),
            path=environ.get("PATH_INFO"),
            query=environ.get("QUERY_STRING") or None,
            status=status_code,
            duration_ms=round(request_time.total_seconds() * 1000, 2),
            remote_addr=environ.get("HTTP_X_FORWARDED_FOR")
            or environ.get("REMOTE_ADDR"),
            user_agent=environ.get("HTTP_USER_AGENT"),
            request_id=environ.get("HTTP_X_REQUEST_ID"),
            bytes_sent=getattr(resp, "sent", None),
        )

    def reopen_files(self):
        pass

    def close_on_exec(self):
        pass


# ── Gunicorn settings ─────────────────────────────────────────────────────────
logger_class = StructlogGunicornLogger

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("INVENIO_LOGGING_CONSOLE_LEVEL", "INFO").lower()

worker_class = "sync"
timeout = 60
keepalive = 5
forwarded_allow_ips = "*"
