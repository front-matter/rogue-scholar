"""Tests for Celery logging configuration hooks."""

import logging
from types import SimpleNamespace

import pytest
import structlog

from rogue_scholar import celery_logging


@pytest.fixture(autouse=True)
def _restore_logging_state():
    """Keep global logging state isolated between tests."""
    names = (
        "",
        "invenio",
        "flask",
        "flask.app",
        "werkzeug",
        "opensearch",
        "elasticsearch",
        "celery",
        "celery.task",
        "urllib3.connectionpool",
        "py.warnings",
    )
    state = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
        )
        for name in names
    }

    yield

    for name, (handlers, level) in state.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.setLevel(level)


def test_configure_celery_logging_non_debug_json(monkeypatch):
    monkeypatch.delenv("INVENIO_DEBUG", raising=False)
    monkeypatch.setenv("INVENIO_LOGGING_CONSOLE_LEVEL", "INFO")

    # Seed handlers that should be removed by configure_celery_logging.
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
        logging.getLogger(name).handlers = [logging.StreamHandler()]

    celery_logging.configure_celery_logging()

    root = logging.getLogger()
    assert root.level == logging.INFO
    assert len(root.handlers) == 1
    assert isinstance(
        root.handlers[0].formatter, structlog.stdlib.ProcessorFormatter
    )

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
        assert logging.getLogger(name).handlers == []

    assert logging.getLogger("urllib3.connectionpool").level == logging.ERROR
    assert logging.getLogger("py.warnings").level == logging.ERROR


def test_configure_celery_logging_debug_and_invalid_level(monkeypatch):
    monkeypatch.setenv("INVENIO_DEBUG", "true")
    monkeypatch.setenv("INVENIO_LOGGING_CONSOLE_LEVEL", "not-a-level")
    logging.getLogger("py.warnings").setLevel(logging.INFO)

    celery_logging.configure_celery_logging()

    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
    assert isinstance(
        root.handlers[0].formatter, structlog.stdlib.ProcessorFormatter
    )

    # In debug mode this logger should not be forced to ERROR.
    assert logging.getLogger("py.warnings").level == logging.INFO


def test_bind_task_context_binds_task_id_and_name(monkeypatch):
    captured = {}

    def _bind_contextvars(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        structlog.contextvars, "bind_contextvars", _bind_contextvars
    )

    celery_logging.bind_task_context(
        task_id="task-123", task=SimpleNamespace(name="my.task")
    )

    assert captured == {"task_id": "task-123", "task_name": "my.task"}


def test_clear_task_context_clears_structlog_contextvars(monkeypatch):
    called = {"cleared": False}

    def _clear_contextvars():
        called["cleared"] = True

    monkeypatch.setattr(
        structlog.contextvars, "clear_contextvars", _clear_contextvars
    )

    celery_logging.clear_task_context()

    assert called["cleared"] is True
