# scripts/create_volume_collections.py
"""Create annual volume collections for blog communities in an idempotent way."""

from __future__ import annotations

from datetime import date
from typing import Any

import re
import structlog
from invenio_access.permissions import system_identity
from invenio_communities.collections.records.api import (
    Collection,
    CollectionTree,
)
from invenio_communities.proxies import current_communities
from invenio_db import db
from invenio_rdm_records.proxies import current_community_records_service


log = structlog.get_logger().bind(script="create_volume_collections")

TREE_TITLE = "Annual Volumes"
TREE_SLUG = "annual-volumes"
TREE_ORDER = 10
DEFAULT_START_YEAR = 2020


def get_year_range(year: int) -> str:
    return f"metadata.publication_date:[{year}-01-01 TO {year}-12-31]"


def _iter_communities(page_size: int = 100) -> list[dict[str, Any]]:
    page = 1
    results: list[dict[str, Any]] = []

    while True:
        response = current_communities.service.search(
            system_identity,
            q="*",
            page=page,
            size=page_size,
        )
        hits = list(response.hits)
        if not hits:
            break

        results.extend(hits)

        if len(hits) < page_size:
            break

        page += 1

    return results


def _is_blog_community(community: dict[str, Any]) -> bool:
    type_value = community.get("type")
    if isinstance(type_value, str):
        return type_value == "blog"
    if isinstance(type_value, dict):
        return type_value.get("id") == "blog"

    metadata_type = (community.get("metadata") or {}).get("type")
    if isinstance(metadata_type, str):
        return metadata_type == "blog"
    if isinstance(metadata_type, dict):
        return metadata_type.get("id") == "blog"

    return False


def _start_year_for_community(
    community: dict[str, Any],
    default_start_year: int,
    current_year: int,
) -> int:
    community_id = community["id"]
    first_year = _first_publication_year(community_id)
    if first_year is None:
        return default_start_year

    return max(min(first_year, current_year), 1900)


def _extract_year(value: str | None) -> int | None:
    if not isinstance(value, str):
        return None

    match = re.search(r"(19|20)\d{2}", value)
    if not match:
        return None

    return int(match.group(0))


def _first_publication_year(community_id: str) -> int | None:
    result = current_community_records_service.search(
        system_identity,
        community_id=community_id,
        params={"size": 1, "sort": "oldest"},
    )
    hits = list(result.hits)
    if not hits:
        return None

    metadata = hits[0].get("metadata") or {}
    return _extract_year(metadata.get("publication_date"))


def _get_or_create_tree(community_id: str) -> tuple[CollectionTree, bool]:
    tree = CollectionTree.query.filter_by(
        community_id=community_id,
        slug=TREE_SLUG,
    ).one_or_none()

    if tree is None:
        tree = CollectionTree.create(
            title=TREE_TITLE,
            slug=TREE_SLUG,
            community_id=community_id,
            order=TREE_ORDER,
        )
        db.session.add(tree)
        db.session.flush()
        return tree, True

    changed = False
    if tree.title != TREE_TITLE:
        tree.title = TREE_TITLE
        changed = True
    if tree.order != TREE_ORDER:
        tree.order = TREE_ORDER
        changed = True

    return tree, changed


def _get_or_create_year_collection(
    community_id: str,
    tree_id: str,
    year: int,
) -> str:
    slug = str(year)
    expected_query = get_year_range(year)
    collection = Collection.query.filter_by(
        community_id=community_id,
        tree_id=tree_id,
        slug=slug,
    ).one_or_none()

    if collection is None:
        collection = Collection.create(
            title=slug,
            slug=slug,
            query=expected_query,
            community_id=community_id,
            tree_id=tree_id,
            order=year,
        )
        db.session.add(collection)
        return "created"

    changed = False
    if collection.title != slug:
        collection.title = slug
        changed = True
    if collection.query != expected_query:
        collection.query = expected_query
        changed = True
    if collection.order != year:
        collection.order = year
        changed = True

    return "updated" if changed else "unchanged"


def create_volumes_for_community(
    community: dict[str, Any],
    default_start_year: int = DEFAULT_START_YEAR,
) -> dict[str, int | str]:
    current_year = date.today().year
    community_id = community["id"]
    slug = community.get("slug", community_id)
    start_year = _start_year_for_community(
        community,
        default_start_year=default_start_year,
        current_year=current_year,
    )

    tree, tree_created_or_updated = _get_or_create_tree(community_id)
    created = 0
    updated = 0
    unchanged = 0

    for year in range(start_year, current_year + 1):
        result = _get_or_create_year_collection(
            community_id=community_id,
            tree_id=tree.id,
            year=year,
        )
        if result == "created":
            created += 1
        elif result == "updated":
            updated += 1
        else:
            unchanged += 1

    return {
        "slug": slug,
        "start_year": start_year,
        "tree_changed": int(tree_created_or_updated),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
    }


def run(page_size: int = 100) -> dict[str, int]:
    communities = _iter_communities(page_size=page_size)

    totals = {
        "total": 0,
        "processed": 0,
        "skipped_non_blog": 0,
        "failed": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
    }

    for community in communities:
        totals["total"] += 1

        if not _is_blog_community(community):
            totals["skipped_non_blog"] += 1
            continue

        community_id = community["id"]
        slug = community.get("slug", community_id)

        try:
            result = create_volumes_for_community(community)
            db.session.commit()
            totals["processed"] += 1
            totals["created"] += int(result["created"])
            totals["updated"] += int(result["updated"])
            totals["unchanged"] += int(result["unchanged"])
            log.info("community_processed", **result)
        except Exception as err:  # pragma: no cover - operational script
            db.session.rollback()
            totals["failed"] += 1
            log.error(
                "community_failed",
                slug=slug,
                id=community_id,
                error=str(err),
            )

    log.info("run_summary", **totals)
    return totals


if __name__ == "__main__":
    run()
