"""Additional views."""

import os

from babel import Locale, UnknownLocaleError
from flask import Blueprint
from flask_babel import get_locale

# Module-level cache: vocabulary subject id → {lang: title}
# Populated once at blueprint creation time from the vocabulary YAML files.
_SUBJECT_TITLES: dict = {}


def _load_subject_titles_from_yaml(instance_path: str) -> dict:
    """Load subject title translations from vocabulary YAML files.

    Reads all subjects_*.yaml files from app_data/vocabularies/ and builds
    an in-memory dict mapping subject id → title dict (e.g. {"en": ..., "de": ...}).
    Called once at app startup so no database queries are needed at render time.
    """
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


def _subject_title(subject):
    """Return the translated title of a vocabulary subject in the current UI locale.

    For vocabulary-backed subjects (those with an 'id'), looks up the title dict
    loaded from the vocabulary YAML files and returns the entry for the active
    locale, falling back to the 'subject' field. For free-text subjects (no 'id'),
    returns the 'subject' field directly.
    """
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

    # Populate subject title cache from YAML files once at startup
    _SUBJECT_TITLES.update(_load_subject_titles_from_yaml(app.instance_path))

    app.jinja_env.filters["language_name"] = _language_name
    app.jinja_env.filters["subject_title"] = _subject_title

    # Add URL rules
    return blueprint
