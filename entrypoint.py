"""
InvenioRDM entrypoint for Rogue Scholar.

This script initializes the database, sets up file storage, creates roles and permissions,
creates custom fields, initializes indices and queues, and finally executes the main process.

It is intended to be used in containers without a shell,
and can be run multiple times without side effects.
"""

import os
import sys
import subprocess


def run(cmd: list[str]):
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def main():
    # Database
    run(["invenio", "db", "init", "create"])

    # Files location
    s3_bucket = os.environ.get("INVENIO_S3_BUCKET_NAME")
    if s3_bucket:
        run(
            [
                "invenio",
                "files",
                "location",
                "create",
                "--default",
                "s3-default",
                f"s3://{s3_bucket}",
            ]
        )
    else:
        run(
            [
                "invenio",
                "files",
                "location",
                "create",
                "--default",
                "default",
                "file:///opt/invenio/var/instance/data",
            ]
        )

    # Roles & permissions
    run(["invenio", "roles", "create", "admin"])
    run(["invenio", "access", "allow", "superuser-access", "role", "admin"])
    run(["invenio", "roles", "create", "administration"])
    run(
        [
            "invenio",
            "access",
            "allow",
            "administration-access",
            "role",
            "administration",
        ]
    )
    run(["invenio", "roles", "create", "administration-moderation"])
    run(
        [
            "invenio",
            "access",
            "allow",
            "administration-moderation",
            "role",
            "administration-moderation",
        ]
    )

    # Indices, custom fields, and fixtures
    run(["invenio", "index", "init"])
    run(["invenio", "rdm-records", "custom-fields", "init"])
    run(["invenio", "communities", "custom-fields", "init"])
    run(["invenio", "rdm-records", "fixtures"])
    run(["invenio", "rdm", "rebuild-all-indices"])

    # Queues
    run(["invenio", "queues", "declare"])

    # Exec main process
    if len(sys.argv) > 1:
        os.execvp(sys.argv[1], sys.argv[1:])
    else:
        raise RuntimeError("No command provided to exec")


if __name__ == "__main__":
    main()
