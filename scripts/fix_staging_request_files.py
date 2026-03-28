"""
Fix missing migration 1763728177 on staging DB.

Migration 1763728177 (invenio-requests 12.3.1) was never applied but
74b23178bfbe (which depends on it) is stamped as current head.

This script manually applies the missing DDL:
- Creates request_files table
- Adds bucket_id column to request_metadata
- Creates required indexes and FK constraint
"""

import os
import psycopg2

dsn = os.environ["INVENIO_SQLALCHEMY_DATABASE_URI"].replace(
    "postgresql+psycopg2://", "postgresql://"
)
conn = psycopg2.connect(dsn)
conn.autocommit = False
cur = conn.cursor()

# Check if already applied
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='request_metadata' AND column_name='bucket_id'"
)
if cur.fetchone():
    print("bucket_id already exists - nothing to do")
    conn.close()
    exit(0)

print("Applying missing migration 1763728177...")

cur.execute("""
    CREATE TABLE IF NOT EXISTS request_files (
        id UUID NOT NULL,
        json JSONB,
        version_id INTEGER NOT NULL,
        created TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        updated TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        key TEXT NOT NULL,
        record_id UUID NOT NULL,
        object_version_id UUID,
        CONSTRAINT pk_request_files PRIMARY KEY (id),
        CONSTRAINT fk_request_files_object_version_id_files_object
            FOREIGN KEY (object_version_id)
            REFERENCES files_object(version_id) ON DELETE RESTRICT,
        CONSTRAINT fk_request_files_record_id_request_metadata
            FOREIGN KEY (record_id)
            REFERENCES request_metadata(id) ON DELETE RESTRICT
    )
""")
print("Created request_files table")

cur.execute(
    "CREATE INDEX IF NOT EXISTS ix_request_files_object_version_id "
    "ON request_files (object_version_id)"
)
cur.execute(
    "CREATE INDEX IF NOT EXISTS ix_request_files_record_id "
    "ON request_files (record_id)"
)
cur.execute(
    "CREATE UNIQUE INDEX IF NOT EXISTS uidx_request_files_record_id_key "
    "ON request_files (record_id, key)"
)
print("Created request_files indexes")

cur.execute(
    "ALTER TABLE request_metadata ADD COLUMN IF NOT EXISTS bucket_id UUID"
)
cur.execute(
    "CREATE INDEX IF NOT EXISTS ix_request_metadata_bucket_id "
    "ON request_metadata (bucket_id)"
)
cur.execute(
    "ALTER TABLE request_metadata "
    "ADD CONSTRAINT fk_request_metadata_bucket_id_files_bucket "
    "FOREIGN KEY (bucket_id) REFERENCES files_bucket(id) ON DELETE RESTRICT"
)
print("Added bucket_id to request_metadata")

conn.commit()
print("Committed successfully.")

# Verify
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='request_metadata' AND column_name='bucket_id'"
)
print("bucket_id column:", cur.fetchone())
cur.execute("SELECT tablename FROM pg_tables WHERE tablename='request_files'")
print("request_files table:", cur.fetchone())
conn.close()
