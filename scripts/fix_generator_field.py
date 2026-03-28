#!/usr/bin/env python3
"""
Fix rs:generator custom field:
1. communities_metadata: convert string -> {"id": "..."}, remap invalid IDs to "Other"
2. rdm_records_metadata: same conversion (strings only, no invalid IDs found)

Invalid community IDs remapped to "Other": Source, Jachère, Github

Run with:
    python scripts/fix_generator_field.py
"""

import os
import psycopg2

DB_URL = os.environ["INVENIO_SQLALCHEMY_DATABASE_URI"].replace(
    "postgresql+psycopg2://", "postgresql://"
)

# 1a. Communities: convert remaining strings to {"id": "..."}
COMMUNITIES_STRING_FIX_SQL = """
UPDATE communities_metadata
SET json = jsonb_set(
    json,
    '{custom_fields,rs:generator}',
    jsonb_build_object('id', json->'custom_fields'->>'rs:generator')
)
WHERE json->'custom_fields' ? 'rs:generator'
  AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string';
"""

# 1b. Communities: remap invalid IDs to "Other"
COMMUNITIES_REMAP_SQL = """
UPDATE communities_metadata
SET json = jsonb_set(
    json,
    '{custom_fields,rs:generator}',
    '{"id": "Other"}'
)
WHERE json->'custom_fields'->'rs:generator'->>'id' IN ('Source', 'Jachère', 'Github');
"""

# 2. RDM records: convert string -> {"id": "..."}
RDM_STRING_FIX_SQL = """
UPDATE rdm_records_metadata
SET json = jsonb_set(
    json,
    '{custom_fields,rs:generator}',
    jsonb_build_object('id', json->'custom_fields'->>'rs:generator')
)
WHERE json->'custom_fields' ? 'rs:generator'
  AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string';
"""

COUNTS_SQL = """
SELECT
  (SELECT COUNT(*) FROM communities_metadata
   WHERE json->'custom_fields' ? 'rs:generator'
     AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string') AS comm_strings,
  (SELECT COUNT(*) FROM communities_metadata
   WHERE json->'custom_fields'->'rs:generator'->>'id' IN ('Source', 'Jachère', 'Github')) AS comm_invalid,
  (SELECT COUNT(*) FROM rdm_records_metadata
   WHERE json->'custom_fields' ? 'rs:generator'
     AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string') AS rdm_strings;
"""


def main():
    print(f"Connecting to: {DB_URL.split('@')[1]}")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(COUNTS_SQL)
    comm_strings, comm_invalid, rdm_strings = cur.fetchone()
    print(f"Communities with string rs:generator:  {comm_strings}")
    print(f"Communities with invalid generator ID: {comm_invalid}")
    print(f"RDM records with string rs:generator:  {rdm_strings}")

    if comm_strings == 0 and comm_invalid == 0 and rdm_strings == 0:
        print("Nothing to fix.")
        cur.close()
        conn.close()
        return

    cur.execute(COMMUNITIES_STRING_FIX_SQL)
    print(f"Communities string->object: {cur.rowcount} rows")

    cur.execute(COMMUNITIES_REMAP_SQL)
    print(f"Communities invalid->Other: {cur.rowcount} rows")

    cur.execute(RDM_STRING_FIX_SQL)
    print(f"RDM records string->object: {cur.rowcount} rows")

    confirm = input("Commit? [y/N] ").strip().lower()
    if confirm == "y":
        conn.commit()
        print("Committed.")
    else:
        conn.rollback()
        print("Rolled back.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
