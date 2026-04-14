"""Enable child communities for all communities in a paginated, safe way."""

from typing import Any

import structlog
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities


log = structlog.get_logger().bind(script="enable_collections")


def _is_blog_community(community: dict[str, Any]) -> bool:
    """Return True when the community is a blog community."""
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


def _iter_communities(page_size: int = 100) -> list[dict[str, Any]]:
    """Return all blog communities by paging through the service search API."""
    page = 1
    all_results: list[dict[str, Any]] = []

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

        all_results.extend(hits)

        if len(hits) < page_size:
            break

        page += 1

    return [
        community for community in all_results if _is_blog_community(community)
    ]


def enable_children_for_all_blogs() -> dict[str, int]:
    """Set ``children.allow=True`` for all communities and return run stats."""
    communities = _iter_communities(page_size=100)
    updated = 0
    skipped = 0
    failed = 0

    for community in communities:
        community_id = community["id"]
        slug = community.get("slug", community_id)
        children = community.get("children") or {}

        if children.get("allow") is True:
            skipped += 1
            log.info(
                "skip_community",
                slug=slug,
                id=community_id,
                reason="already_enabled",
            )
            continue

        try:
            full = current_communities.service.read(
                system_identity, id_=community_id
            ).to_dict()
            # Strip read-only fields that update() rejects
            for key in (
                "id",
                "links",
                "revision_id",
                "created",
                "updated",
                "versions",
            ):
                full.pop(key, None)
            full.setdefault("children", {})["allow"] = True
            current_communities.service.update(
                system_identity,
                id_=community_id,
                data=full,
            )
            updated += 1
            log.info("update_community", slug=slug, id=community_id)
        except Exception as err:  # pragma: no cover - operational script
            failed += 1
            log.error(
                "update_failed", slug=slug, id=community_id, error=str(err)
            )

    stats = {
        "total": len(communities),
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
    log.info("run_summary", **stats)
    return stats


if __name__ == "__main__":
    enable_children_for_all_blogs()
