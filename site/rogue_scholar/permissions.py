# -*- coding: utf-8 -*-
#
# Copyright (C) 2025-2026 Front Matter.
#
# Rogue Scholar is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Rogue Scholar permissions."""

from invenio_communities.permissions import CommunityPermissionPolicy
from invenio_rdm_records.services.generators import (
    AccessGrant,
    RecordOwners,
)
from invenio_rdm_records.services.permissions import RDMRecordPermissionPolicy
from invenio_records_permissions.generators import (
    SystemProcess,
)
from .generators import (
    MediaFilesManager,
)


class RogueScholarRecordPermissionPolicy(RDMRecordPermissionPolicy):
    """Access control configuration for records."""

    #
    # High-level permissions (used by low-level)
    #
    can_manage = [SystemProcess()]
    can_curate = [SystemProcess()]
    can_review = [SystemProcess()]
    can_preview = [SystemProcess()]

    #
    #  Records
    #

    # Used for search filtering of deleted records
    # cannot be implemented inside can_read - otherwise permission will
    # kick in before tombstone renders
    can_create = [SystemProcess()]
    can_read_deleted = [SystemProcess()]
    can_read_deleted_files = can_read_deleted
    can_media_read_deleted_files = can_read_deleted_files

    #
    # Drafts
    #
    # Allow reading metadata of a draft
    can_read_draft = can_preview
    # Allow reading files of a draft
    can_draft_read_files = can_preview + [SystemProcess()]
    # Allow updating metadata of a draft
    can_update_draft = can_review
    # Allow uploading, updating and deleting files in drafts
    can_draft_create_files = can_review
    can_draft_set_content_files = [SystemProcess()]
    can_draft_get_content_files = [SystemProcess()]
    can_draft_commit_files = [SystemProcess()]
    can_draft_update_files = can_review
    can_draft_delete_files = can_review
    can_manage_record_access = can_review

    #
    # PIDs
    #
    can_pid_create = can_review
    can_pid_register = can_review
    can_pid_update = can_review
    can_pid_discard = can_review
    can_pid_delete = can_review

    #
    # Actions
    #
    # Allow to put a record in edit mode (create a draft from record)
    can_edit = [SystemProcess()]
    # Allow deleting/discarding a draft and all associated files
    can_delete_draft = [SystemProcess()]
    # Allow creating a new version of an existing published record.
    can_new_version = [SystemProcess()]
    # Allow publishing a new record or changes to an existing record.
    can_publish = [SystemProcess()]
    # Allow lifting a record or draft.
    can_lift_embargo = [SystemProcess()]

    #
    # Record communities
    #
    # Who can add record to a community
    can_add_community = can_review

    # Media files
    can_draft_media_create_files = [MediaFilesManager(), SystemProcess()]
    can_draft_media_read_files = can_draft_media_create_files
    can_draft_media_set_content_files = [SystemProcess()]
    can_draft_media_commit_files = [SystemProcess()]
    can_draft_media_update_files = can_draft_media_create_files
    can_draft_media_delete_files = can_draft_media_create_files
    can_moderate = [SystemProcess()]
    can_media_create_files = [SystemProcess()]
    can_media_set_content_files = [SystemProcess()]
    can_media_commit_files = [SystemProcess()]
    can_media_update_files = [SystemProcess()]
    can_media_delete_files = [SystemProcess()]
    can_modify_locked_files = [SystemProcess()]


class RogueScholarCommunityPermissionPolicy(CommunityPermissionPolicy):
    """Permissions for Community CRUD operations.
    Communities can only be created by the system, records can only
    be managed by the system.
    """

    # Community
    can_create = [SystemProcess()]
    can_submit_record = [SystemProcess()]
    can_community_manage_record = [SystemProcess()]

    # Records in community
    can_update = [SystemProcess()]
    can_delete = [SystemProcess()]
