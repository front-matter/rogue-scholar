# scripts/create_volume_collections.py
"""Create volume collections for blog communities in an idempotent way."""

from __future__ import annotations

from typing import Any

import re
import structlog
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_collections.api import Collection, CollectionTree
from invenio_collections.errors import (
    CollectionNotFound,
    CollectionTreeNotFound,
)
from invenio_db import db
from invenio_rdm_records.proxies import current_community_records_service


log = structlog.get_logger().bind(script="create_volume_collections")

TREE_TITLE = "Volumes"
TREE_SLUG = "volumes"
TREE_ORDER = 10


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
    current_year: int,
) -> int | None:
    community_id = community["id"]
    first_year = _first_publication_year(community_id)
    if first_year is None:
        return None

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


def _newest_publication_year(community_id: str) -> int | None:
    result = current_community_records_service.search(
        system_identity,
        community_id=community_id,
        params={"size": 1, "sort": "newest"},
    )
    hits = list(result.hits)
    if not hits:
        return None

    metadata = hits[0].get("metadata") or {}
    return _extract_year(metadata.get("publication_date"))


def _get_or_create_tree(community_id: str) -> tuple[CollectionTree, bool]:
    try:
        tree = CollectionTree.resolve(
            slug=TREE_SLUG,
            community_id=community_id,
        )
    except CollectionTreeNotFound:
        tree = CollectionTree.create(
            title=TREE_TITLE,
            slug=TREE_SLUG,
            community_id=community_id,
            order=TREE_ORDER,
        )
        return tree, True

    updates: dict[str, Any] = {}
    if tree.title != TREE_TITLE:
        updates["title"] = TREE_TITLE
    if tree.order != TREE_ORDER:
        updates["order"] = TREE_ORDER

    if updates:
        tree.update(**updates)
        return tree, True

    return tree, False


def _get_or_create_year_collection(
    tree: CollectionTree,
    year: int,
) -> str:
    slug = str(year)
    expected_query = get_year_range(year)

    try:
        collection = Collection.read(slug=slug, ctree_id=tree.id)
    except CollectionNotFound:
        Collection.create(
            title=slug,
            slug=slug,
            query=expected_query,
            ctree=tree,
            order=year,
        )
        return "created"

    updates: dict[str, Any] = {}
    if collection.title != slug:
        updates["title"] = slug
    if collection.search_query != expected_query:
        updates["search_query"] = expected_query
    if collection.order != year:
        updates["order"] = year

    if updates:
        collection.update(**updates)
        return "updated"

    return "unchanged"


def _refresh_year_collection_sizes(
    tree: CollectionTree,
    start_year: int,
    end_year: int,
) -> int:
    """Recalculate and persist num_records for each yearly collection."""
    updated_sizes = 0

    for year in range(start_year, end_year + 1):
        slug = str(year)
        collection = Collection.read(slug=slug, ctree_id=tree.id)
        search_result = current_community_records_service.search(
            system_identity,
            community_id=tree.community_id,
            extra_filter=collection.query,
            params={"size": 1},
        )
        total = int(search_result.total)

        if collection.num_records != total:
            collection.update(num_records=total)
            updated_sizes += 1

    return updated_sizes


def create_volumes_for_community(
    community: dict[str, Any],
    start_year: int,
    end_year: int,
) -> dict[str, int | str]:
    community_id = community["id"]
    slug = community.get("slug", community_id)

    tree, tree_created_or_updated = _get_or_create_tree(community_id)
    created = 0
    updated = 0
    unchanged = 0
    size_updates = 0

    for year in range(start_year, end_year + 1):
        result = _get_or_create_year_collection(
            tree=tree,
            year=year,
        )
        if result == "created":
            created += 1
        elif result == "updated":
            updated += 1
        else:
            unchanged += 1

    size_updates = _refresh_year_collection_sizes(
        tree=tree,
        start_year=start_year,
        end_year=end_year,
    )

    return {
        "slug": slug,
        "start_year": start_year,
        "end_year": end_year,
        "tree_changed": int(tree_created_or_updated),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "size_updates": size_updates,
    }


def run(page_size: int = 100) -> dict[str, int]:
    communities = _iter_communities(page_size=page_size)

    totals = {
        "total": 0,
        "processed": 0,
        "skipped_non_blog": 0,
        "skipped_no_first_post": 0,
        "skipped_no_last_post": 0,
        "skipped_invalid_year_bounds": 0,
        "failed": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "size_updates": 0,
    }

    current_year = date.today().year

    for community in communities:
        totals["total"] += 1

        if not _is_blog_community(community):
            totals["skipped_non_blog"] += 1
            continue

        start_year = _start_year_for_community(
            community,
            current_year=current_year,
        )
        if start_year is None:
            totals["skipped_no_first_post"] += 1
            log.info(
                "skip_community",
                slug=community.get("slug", community["id"]),
                id=community["id"],
                reason="missing_first_publication_date",
            )
            continue

        end_year = _newest_publication_year(community["id"])
        if end_year is None:
            totals["skipped_no_last_post"] += 1
            log.info(
                "skip_community",
                slug=community.get("slug", community["id"]),
                id=community["id"],
                reason="missing_latest_publication_date",
            )
            continue

        if start_year > end_year:
            totals["skipped_invalid_year_bounds"] += 1
            log.info(
                "skip_community",
                slug=community.get("slug", community["id"]),
                id=community["id"],
                reason="invalid_year_bounds",
                start_year=start_year,
                end_year=end_year,
            )
            continue

        community_id = community["id"]
        slug = community.get("slug", community_id)

        try:
            result = create_volumes_for_community(
                community,
                start_year=start_year,
                end_year=end_year,
            )
            db.session.commit()
            totals["processed"] += 1
            totals["created"] += int(result["created"])
            totals["updated"] += int(result["updated"])
            totals["unchanged"] += int(result["unchanged"])
            totals["size_updates"] += int(result["size_updates"])
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
