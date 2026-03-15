# -*- coding: utf-8 -*-
#
# Copyright (C) 2025-2026 Front Matter.
#
# Rogue Scholar is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Rogue Scholar custom permission generators."""

from invenio_access import action_factory
from invenio_records.dictutils import dict_lookup
from invenio_records_permissions.generators import (
    ConditionalGenerator,
    Generator,
)

# these are defined here as there is a circular dependency otherwise with the
# permissions.py file
media_files_management_action = action_factory("manage-media-files")


class MediaFilesManager(Generator):
    """Allows media files management."""

    def __init__(self):
        """Constructor."""
        super(MediaFilesManager, self).__init__()

    def needs(self, **kwargs):
        """Enabling Needs."""
        return [media_files_management_action]


class IfRecordManagementAllowedForCommunity(ConditionalGenerator):
    """Conditional generator for community access to record management."""

    def _condition(self, **kwargs):
        """Check if community can manage the migrated record."""
        record = kwargs.get("record")
        if record is None:
            return False
        try:
            can_community_manage_record = dict_lookup(
                record.parent, "permission_flags.can_community_manage_record"
            )
        except KeyError, AttributeError, TypeError:
            # Keep permissive fallback for legacy records lacking flags/parent.
            can_community_manage_record = True

        return bool(can_community_manage_record)

    def query_filter(self, **kwargs):
        """Filters for current identity as super user."""
        then_query = self._make_query(self.then_, **kwargs)
        else_query = self._make_query(self.else_, **kwargs)

        return then_query if then_query else else_query
