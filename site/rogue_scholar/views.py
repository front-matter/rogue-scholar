"""Additional views."""

import os
from functools import wraps
from pathlib import Path

from babel import Locale, UnknownLocaleError
from flask import Blueprint, abort, current_app, render_template, request
from flask_babel import get_locale
from invenio_administration.permissions import administration_permission
from prometheus_flask_exporter.multiprocess import (
    GunicornPrometheusMetrics,
    GunicornInternalPrometheusMetrics,
)

# Module-level cache: vocabulary subject id -> {lang: title}
# Populated once at blueprint creation time from the vocabulary YAML files.
_SUBJECT_TITLES: dict = {}


def _load_subject_titles_from_yaml(instance_path: str) -> dict:
    """Load subject title translations from vocabulary YAML files."""
    try:
        import yaml
    except ImportError:
        return {}

    titles: dict = {}
    vocab_dir = os.path.join(instance_path, "app_data", "vocabularies")
    if not os.path.isdir(vocab_dir):
        return titles

    for fname in os.listdir(vocab_dir):
        if not (fname.startswith("subjects_") and fname.endswith(".yaml")):
            continue
        try:
            with open(os.path.join(vocab_dir, fname), encoding="utf-8") as fh:
                entries = yaml.safe_load(fh) or []
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and "id" in entry
                    and "title" in entry
                ):
                    titles[entry["id"]] = entry["title"]
        except Exception:
            pass
    return titles


def _language_name(lang_id):
    """Return the display name of a language ID in the current UI locale."""
    try:
        ui_locale = str(get_locale() or "en")
        loc = Locale.parse(ui_locale)
        normalized = Locale.parse(lang_id).language
        name = loc.languages.get(normalized)
        return name if name else lang_id
    except UnknownLocaleError, ValueError:
        return lang_id


def _subject_title(subject):
    """Return the translated title of a vocabulary subject in the current UI locale."""
    fallback = subject.get("subject", "")
    subject_id = subject.get("id")
    if not subject_id:
        return fallback
    try:
        lang = str(get_locale() or "en").split("_")[0]
        titles = _SUBJECT_TITLES.get(subject_id, {})
        return titles.get(lang) or fallback
    except Exception:
        return fallback


def _overview():
    """Overview page with locale-based template selection."""
    locale = get_locale()
    return render_template(
        [
            f"invenio_app_rdm/overview/overview.{locale}.html",
            "invenio_app_rdm/overview/overview.en.html",
        ]
    )


def _board():
    """Advisory Board page with locale-based template selection."""
    locale = get_locale()
    return render_template(
        [
            f"invenio_app_rdm/board/board.{locale}.html",
            "invenio_app_rdm/board/board.en.html",
        ]
    )


def _faq():
    """FAQ page with locale-based template selection."""
    locale = get_locale()
    return render_template(
        [
            f"invenio_app_rdm/faq/faq.{locale}.html",
            "invenio_app_rdm/faq/faq.en.html",
        ]
    )


def _metrics_access(f):
    """Allow direct internal requests; require admin permission via proxy."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get("X-Forwarded-For"):
            # Request came through the upstream proxy — enforce auth
            if not administration_permission.can():
                abort(403)
        return f(*args, **kwargs)

    return decorated


def _init_metrics(app, **kwargs):
    """Initialize API metrics using Gunicorn multiprocess mode."""
    _ensure_multiproc_dir()
    return GunicornInternalPrometheusMetrics(app, **kwargs)


def _ensure_multiproc_dir():
    """Ensure Prometheus multiprocess directory exists and is configured."""
    multiproc_dir = (
        os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        or os.environ.get("prometheus_multiproc_dir")
        or "/tmp/prometheus_multiproc"
    )
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", multiproc_dir)
    Path(multiproc_dir).mkdir(parents=True, exist_ok=True)
    return multiproc_dir


def _version():
    """Return the configured InvenioRDM version string."""
    return str(current_app.config.get("INVENIO_APP_RDM_VERSION", ""))


def create_api_blueprint(app):
    """Register Prometheus metrics on the API Flask app."""
    _init_metrics(
        app,
        path="/metrics",
        group_by="endpoint",
        metrics_decorator=_metrics_access,
    )
    # Disable HTTPS redirect for the metrics endpoint on the API app.
    # In the combined app this is exposed externally as /api/metrics.
    metrics_view = app.view_functions.get("prometheus_metrics")
    if metrics_view is not None:
        metrics_view.talisman_view_options = {"force_https": False}

    blueprint = Blueprint("rogue_scholar_api", __name__)
    blueprint.add_url_rule("/version", endpoint="version", view_func=_version)

    return blueprint


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    # Track UI app requests in the shared multiprocess registry without
    # exposing an endpoint on the UI app.
    _ensure_multiproc_dir()
    GunicornPrometheusMetrics(app, group_by="endpoint", export_defaults=True)

    blueprint = Blueprint(
        "rogue_scholar",
        __name__,
        template_folder="./templates",
    )

    _SUBJECT_TITLES.update(_load_subject_titles_from_yaml(app.instance_path))

    app.jinja_env.filters["language_name"] = _language_name
    app.jinja_env.filters["subject_title"] = _subject_title

    blueprint.add_url_rule(
        "/overview", endpoint="overview", view_func=_overview
    )
    blueprint.add_url_rule("/board", endpoint="board", view_func=_board)
    blueprint.add_url_rule("/faq", endpoint="faq", view_func=_faq)

    return blueprint
