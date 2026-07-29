from app.models.enums import RiskTier
from app.risk_engine.catalog import CATALOG, UnknownActionRatingError
from app.risk_engine.scoring import RiskRating, compute_score

AUTOMATIC_THRESHOLD = 2
APPROVAL_THRESHOLD = 8


def classify(rating: RiskRating) -> tuple[float, RiskTier]:
    score = compute_score(rating)

    # a hard irreversibility floor overrides the numeric score entirely
    if rating.reversibility == 1 or score > APPROVAL_THRESHOLD:
        return score, RiskTier.forbidden

    if score <= AUTOMATIC_THRESHOLD and not rating.sensitive:
        return score, RiskTier.automatic

    return score, RiskTier.approval


def classify_action(tool: str, profile: str) -> tuple[float, RiskTier, RiskRating]:
    key = f"{tool}:{profile}"
    rating = CATALOG.get(key)
    if rating is None:
        raise UnknownActionRatingError(key)

    score, tier = classify(rating)
    return score, tier, rating
