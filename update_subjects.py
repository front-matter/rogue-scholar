#!/usr/bin/env python3
"""Update existing subject vocabulary entries (upsert).

Usage:
    invenio shell update_subjects.py [--scheme SCHEME]

Examples:
    invenio shell update_subjects.py
    invenio shell update_subjects.py --scheme Topics
    invenio shell update_subjects.py --scheme FOS

Unlike `invenio rdm-records add-to-fixture subjects.Topics`, this script
handles both create (new entries) and update (existing entries) correctly.
The built-in command always calls service.create() for subjects (no "type"
key in data), causing PIDAlreadyExists errors for existing entries.
"""

import sys
import yaml
from pathlib import Path

from invenio_access.permissions import system_identity
from invenio_records_resources.proxies import current_service_registry

# ---------------------------------------------------------------------------
# Scheme → data-file mapping (mirrors app_data/vocabularies.yaml)
# ---------------------------------------------------------------------------
SCHEME_FILES = {
    "FOS": "app_data/vocabularies/subjects_oecd_fos.yaml",
    "Domains": "app_data/vocabularies/subjects_openalex_domains.yaml",
    "Fields": "app_data/vocabularies/subjects_openalex_fields.yaml",
    "Subfields": "app_data/vocabularies/subjects_openalex_subfields.yaml",
    "Topics": "app_data/vocabularies/subjects_openalex_topics.yaml",
}

# ---------------------------------------------------------------------------
# Parse CLI arg --scheme
# ---------------------------------------------------------------------------
scheme_filter = None
args = sys.argv[1:]
if "--scheme" in args:
    idx = args.index("--scheme")
    scheme_filter = args[idx + 1]
    schemes_to_run = {scheme_filter: SCHEME_FILES[scheme_filter]}
else:
    schemes_to_run = SCHEME_FILES

service = current_service_registry.get("subjects")

for scheme, filepath in schemes_to_run.items():
    path = Path(filepath)
    if not path.exists():
        print(f"[SKIP] {filepath} not found")
        continue

    with open(path, encoding="utf-8") as f:
        entries = yaml.safe_load(f) or []

    created = updated = errors = 0

    for data in entries:
        entry_id = data["id"]
        try:
            # Try to read → update if exists
            service.read(system_identity, entry_id)
            service.update(system_identity, entry_id, data=data)
            updated += 1
        except Exception:
            # Not found → create
            try:
                service.create(system_identity, data)
                created += 1
            except Exception as e:
                print(f"  [ERROR] create {entry_id}: {e}")
                errors += 1

    print(
        f"[{scheme}] created={created} updated={updated} errors={errors} "
        f"(total={len(entries)})"
    )
