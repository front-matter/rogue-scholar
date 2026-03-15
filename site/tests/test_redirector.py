"""Tests for legacy redirector helpers and route definitions."""

from flask import Flask, request

from rogue_scholar import redirector


def _fake_url_for(endpoint, **values):
    return {"endpoint": endpoint, "values": values}


def test_camelcase_to_titlecase_converts_expected_value():
    assert (
        redirector.camelcase_to_titlecase("openAlexTopics")
        == "Open alex topics"
    )


def test_blogs_search_view_function_builds_query_and_filter(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(redirector, "url_for", _fake_url_for)

    with app.test_request_context(
        "/blogs?query=climate&category=openAlexTopics&page=2"
    ):
        target = redirector.blogs_search_view_function()

    assert target == {
        "endpoint": "invenio_communities.communities_search",
        "values": {"q": "climate", "f": "subject:Open alex topics", "p": "2"},
    }


def test_posts_search_view_function_prefers_tags_over_category(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(redirector, "url_for", _fake_url_for)

    with app.test_request_context(
        "/posts?query=ai&category=openAlexFields&tags=Physics&page=7"
    ):
        target = redirector.posts_search_view_function()

    assert target == {
        "endpoint": "invenio_search_ui.search",
        "values": {"q": "ai", "f": "subject:Physics", "p": "7"},
    }


def test_posts_detail_view_function_uses_view_args_for_doi(monkeypatch):
    app = Flask(__name__)
    monkeypatch.setattr(redirector, "url_for", _fake_url_for)

    with app.test_request_context("/posts/10.1234/abc"):
        request.view_args = {"prefix": "10.1234", "suffix": "abc"}
        target = redirector.posts_detail_view_function()

    assert target == {
        "endpoint": "invenio_search_ui.search",
        "values": {"q": "doi:10.1234/abc"},
    }


def test_redirector_rules_include_core_and_localized_routes():
    rules = redirector.REDIRECTOR_RULES

    assert rules["redirect_blogs"]["source"] == "/blogs"
    assert rules["redirect_posts"]["source"] == "/posts"
    assert (
        rules["redirect_posts_search"]["source"] == "/posts/<prefix>/<suffix>"
    )

    for locale in redirector.LOCALES:
        assert rules[f"redirect_{locale}"]["source"] == f"/{locale}"
        assert (
            rules[f"redirect_{locale}_blogs"]["source"] == f"/{locale}/blogs"
        )
        assert (
            rules[f"redirect_{locale}_posts_search"]["source"]
            == f"/{locale}/posts/<prefix>/<suffix>"
        )
