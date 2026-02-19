"""Additional views."""

from functools import lru_cache

from babel import Locale, UnknownLocaleError
from flask import Blueprint
from flask_babel import get_locale
from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry


def _language_name(lang_id):
    """Return the display name of a language ID in the current UI locale.

    Uses Babel to translate ISO 639-2/3 language codes (e.g. 'deu', 'eng')
    into a human-readable name in the currently active Flask-Babel locale.
    Falls back to the language ID itself if no translation is found.
    """
    try:
        ui_locale = str(get_locale() or "en")
        loc = Locale.parse(ui_locale)
        name = loc.languages.get(lang_id)
        return name if name else lang_id
    except (UnknownLocaleError, ValueError):
        return lang_id


@lru_cache(maxsize=2000)
def _get_subject_titles(subject_id):
    """Return the title dict for a vocabulary subject ID (cached)."""
    try:
        service = current_service_registry.get("subjects")
        result = service.read(system_identity, subject_id)
        return result.data.get("title", {})
    except Exception:
        return {}


def _subject_title(subject):
    """Return the translated title of a vocabulary subject in the current UI locale.

    For vocabulary-backed subjects (those with an 'id'), looks up the full
    title dict and returns the entry for the active locale, falling back
    to the 'subject' field. For free-text subjects (no 'id'), returns
    the 'subject' field directly.
    """
    fallback = subject.get("subject", "")
    subject_id = subject.get("id")
    if not subject_id:
        return fallback
    try:
        lang = str(get_locale() or "en").split("_")[0]
        titles = _get_subject_titles(subject_id)
        return titles.get(lang) or fallback
    except Exception:
        return fallback


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""
    blueprint = Blueprint(
        "invenio_rdm_starter",
        __name__,
        template_folder="./templates",
    )

    app.jinja_env.filters["language_name"] = _language_name
    app.jinja_env.filters["subject_title"] = _subject_title

    # Add URL rules
    return blueprint
