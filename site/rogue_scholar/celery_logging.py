import logging
import os

import structlog
from celery.signals import setup_logging, task_postrun, task_prerun


@setup_logging.connect
def configure_celery_logging(**kwargs):
    """Replace Celery's default logging with structlog JSON (or console) output."""
    log_level_name = os.environ.get(
        "INVENIO_LOGGING_CONSOLE_LEVEL", "INFO"
    ).upper()
    log_level = getattr(logging, log_level_name, logging.WARNING)
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

    # Remove any handlers that Flask/InvenioRDM may have attached to child
    # loggers during app initialisation (they use the old bracket format and
    # would produce duplicate lines alongside the root structlog handler).
    for name in (
        "invenio",
        "flask",
        "flask.app",
        "werkzeug",
        "opensearch",
        "elasticsearch",
        "celery",
        "celery.task",
    ):
        lg = logging.getLogger(name)
        lg.handlers = []

    logging.getLogger("invenio").setLevel(max(log_level, logging.INFO))
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
    if not debug_mode:
        logging.getLogger("py.warnings").setLevel(logging.ERROR)


@task_prerun.connect
def bind_task_context(task_id, task, **kwargs):
    """Bind task identity to structlog context vars for the duration of the task."""
    structlog.contextvars.bind_contextvars(
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def clear_task_context(**kwargs):
    """Clear structlog context vars after each task."""
    structlog.contextvars.clear_contextvars()
