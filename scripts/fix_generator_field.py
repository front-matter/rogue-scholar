#!/usr/bin/env python3
"""
Fix communities_metadata: convert rs:generator from plain string
to {"id": "..."} dict as required by VocabularyCF.

Run with:
    python scripts/fix_generator_field.py
"""

import os
import psycopg2

DB_URL = os.environ["INVENIO_SQLALCHEMY_DATABASE_URI"].replace(
    "postgresql+psycopg2://", "postgresql://"
)

FIX_SQL = """
UPDATE communities_metadata
SET json = jsonb_set(
    json,
    '{custom_fields,rs:generator}',
    jsonb_build_object('id', json->'custom_fields'->>'rs:generator')
)
WHERE json->'custom_fields' ? 'rs:generator'
  AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string';
"""

COUNT_BEFORE_SQL = """
SELECT COUNT(*) FROM communities_metadata
WHERE json->'custom_fields' ? 'rs:generator'
  AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'string';
"""

COUNT_AFTER_SQL = """
SELECT COUNT(*) FROM communities_metadata
WHERE json->'custom_fields' ? 'rs:generator'
  AND jsonb_typeof(json->'custom_fields'->'rs:generator') = 'object';
"""


def main():
    print(f"Connecting to: {DB_URL.split('@')[1]}")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(COUNT_BEFORE_SQL)
    count_before = cur.fetchone()[0]
    print(f"Communities with string rs:generator (before): {count_before}")

    if count_before == 0:
        print("Nothing to fix; all rs:generator values are already objects.")
        cur.close()
        conn.close()
        return

    cur.execute(FIX_SQL)
    print(f"Rows updated: {cur.rowcount}")

    cur.execute(COUNT_AFTER_SQL)
    count_after = cur.fetchone()[0]
    print(f"Communities with object rs:generator (after):  {count_after}")

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
