import pytest

from app.models.enums import EngagementStatus, RiskTier
from app.state_machine.engagement import InvalidTransitionError, next_status_after_action


def test_first_action_always_leaves_scope_validation():
    result = next_status_after_action(EngagementStatus.scope_validation, RiskTier.automatic)
    assert result == EngagementStatus.reconnaissance


def test_automatic_action_moves_reconnaissance_to_scan():
    result = next_status_after_action(EngagementStatus.reconnaissance, RiskTier.automatic)
    assert result == EngagementStatus.scan


def test_repeated_automatic_action_stays_in_scan():
    result = next_status_after_action(EngagementStatus.scan, RiskTier.automatic)
    assert result == EngagementStatus.scan


def test_approval_tier_action_pauses_at_approval_pending():
    result = next_status_after_action(EngagementStatus.scan, RiskTier.approval)
    assert result == EngagementStatus.approval_pending


def test_approval_tier_action_during_exploitation_pauses_again():
    result = next_status_after_action(EngagementStatus.exploitation, RiskTier.approval)
    assert result == EngagementStatus.approval_pending


def test_forbidden_tier_raises():
    with pytest.raises(ValueError):
        next_status_after_action(EngagementStatus.scan, RiskTier.forbidden)


def test_closed_engagement_has_no_valid_forward_transition():
    with pytest.raises(InvalidTransitionError):
        next_status_after_action(EngagementStatus.closed, RiskTier.approval)
