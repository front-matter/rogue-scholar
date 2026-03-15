"""Tests for Prometheus metrics endpoint wiring."""

from unittest.mock import patch

import pytest


def test_api_metrics_endpoint_exists(base_client):
    response = base_client.get("/api/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.content_type


def test_api_metrics_requires_admin_when_forwarded(base_client):
    with patch(
        "rogue_scholar.views.administration_permission.can",
        return_value=False,
    ):
        response = base_client.get(
            "/api/metrics",
            headers={"X-Forwarded-For": "10.0.0.1"},
        )

    assert response.status_code == 403


def test_api_metrics_allows_admin_when_forwarded(base_client):
    with patch(
        "rogue_scholar.views.administration_permission.can",
        return_value=True,
    ):
        response = base_client.get(
            "/api/metrics",
            headers={"X-Forwarded-For": "10.0.0.1"},
        )

    assert response.status_code == 200


def test_ui_app_does_not_expose_metrics_endpoint(base_app):
    routes = {rule.rule for rule in base_app.url_map.iter_rules()}
    assert "/metrics" not in routes
