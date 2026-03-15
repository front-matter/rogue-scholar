"""Tests for Rogue Scholar permission generators and policy wiring."""

from types import SimpleNamespace

from rogue_scholar.generators import (
    IfRecordManagementAllowedForCommunity,
    MediaFilesManager,
    media_files_management_action,
)
from rogue_scholar.permissions import RogueScholarRecordPermissionPolicy


class _BoomRecord:
    @property
    def parent(self):
        raise AttributeError("no parent")


def test_media_files_manager_needs_contains_expected_action():
    generator = MediaFilesManager()

    assert generator.needs() == [media_files_management_action]


def test_record_management_condition_denies_when_record_missing():
    generator = IfRecordManagementAllowedForCommunity(then_=[], else_=[])

    assert generator._condition(record=None) is False


def test_record_management_condition_uses_permission_flag_when_present():
    generator = IfRecordManagementAllowedForCommunity(then_=[], else_=[])
    allowed_record = SimpleNamespace(
        parent={"permission_flags": {"can_community_manage_record": True}}
    )
    denied_record = SimpleNamespace(
        parent={"permission_flags": {"can_community_manage_record": False}}
    )

    assert generator._condition(record=allowed_record) is True
    assert generator._condition(record=denied_record) is False


def test_record_management_condition_falls_back_to_true_for_legacy_records():
    generator = IfRecordManagementAllowedForCommunity(then_=[], else_=[])

    assert generator._condition(record=SimpleNamespace(parent={})) is True
    assert generator._condition(record=_BoomRecord()) is True


def test_permission_policy_uses_custom_generators():
    manage_generator = RogueScholarRecordPermissionPolicy.can_manage[0]
    media_generator = (
        RogueScholarRecordPermissionPolicy.can_draft_media_create_files[0]
    )

    assert isinstance(manage_generator, IfRecordManagementAllowedForCommunity)
    assert isinstance(media_generator, MediaFilesManager)
