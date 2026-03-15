"""Pytest fixtures for Rogue Scholar endpoint tests."""

import os

import pytest
from invenio_app import factory as app_factory


@pytest.fixture(scope="module")
def app_config(app_config):
    """Application configuration for endpoint tests."""
    app_config["REST_CSRF_ENABLED"] = False
    app_config["WTF_CSRF_ENABLED"] = False
    app_config["INVENIO_APP_RDM_VERSION"] = "14.0.0-test"
    os.environ.setdefault(
        "PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc"
    )
    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory used by pytest-invenio."""
    return app_factory.create_app
