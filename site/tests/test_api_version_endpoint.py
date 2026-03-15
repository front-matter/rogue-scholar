"""Tests for API version endpoint."""

from unittest.mock import patch


def test_api_version_endpoint_returns_configured_string(base_client, base_app):
    response = base_client.get("/api/version")

    assert response.status_code == 200
    assert (
        response.get_data(as_text=True)
        == base_app.config["INVENIO_APP_RDM_VERSION"]
    )


def test_api_version_requires_no_auth_when_forwarded(base_client, base_app):
    with patch(
        "rogue_scholar.views.administration_permission.can",
        return_value=False,
    ):
        response = base_client.get(
            "/api/version",
            headers={"X-Forwarded-For": "10.0.0.1"},
        )

    assert response.status_code == 200
    assert (
        response.get_data(as_text=True)
        == base_app.config["INVENIO_APP_RDM_VERSION"]
    )
