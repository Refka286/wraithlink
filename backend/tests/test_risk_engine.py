import pytest

from app.models.enums import RiskTier
from app.risk_engine.catalog import UnknownActionRatingError
from app.risk_engine.engine import classify_action


@pytest.mark.parametrize(
    "tool,profile,expected_score,expected_tier",
    [
        ("nmap", "syn-stealth", 0.4, RiskTier.automatic),
        ("ldap", "anonymous-enum", 0.2, RiskTier.automatic),
        ("sqlmap", "aggressive", 3.0, RiskTier.approval),
        ("netexec", "kerberoast", 1.2, RiskTier.approval),
        ("ad", "bruteforce-massive", 10.0, RiskTier.forbidden),
        ("netexec", "dcsync", 5.0, RiskTier.forbidden),
    ],
)
def test_classify_action_matches_plan_examples(tool, profile, expected_score, expected_tier):
    score, tier, _ = classify_action(tool, profile)

    assert score == pytest.approx(expected_score)
    assert tier == expected_tier


def test_classify_action_unknown_key_raises():
    with pytest.raises(UnknownActionRatingError):
        classify_action("unknown-tool", "unknown-profile")


def test_kerberoast_is_never_automatic_even_though_score_is_low():
    score, tier, rating = classify_action("netexec", "kerberoast")

    assert rating.sensitive is True
    assert score <= 2
    assert tier == RiskTier.approval


def test_dcsync_is_forbidden_due_to_irreversibility_not_score_alone():
    score, tier, rating = classify_action("netexec", "dcsync")

    assert rating.reversibility == 1
    assert score < 8
    assert tier == RiskTier.forbidden
