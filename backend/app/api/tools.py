from fastapi import APIRouter, Depends

from app.auth.deps import require_role
from app.knowledge.tools import TOOLS
from app.models.enums import RiskTier, UserRole
from app.models.user import User
from app.risk_engine.catalog import UnknownActionRatingError
from app.risk_engine.engine import APPROVAL_THRESHOLD, AUTOMATIC_THRESHOLD, classify_action
from app.risk_engine.scoring import RiskRating
from app.schemas.tools import ToolOut

router = APIRouter()


def _tier_reason(rating: RiskRating, score: float, tier: RiskTier) -> str:
    # mirrors the exact branching in app.risk_engine.engine.classify(), so
    # this explanation can never drift out of sync with the real logic
    if rating.reversibility == 1:
        return "Action irreversible (reversibilite = 1) : bloquee automatiquement quel que soit le score de risque."
    if score > APPROVAL_THRESHOLD:
        return f"Score de risque ({score:.2f}) superieur au seuil d'interdiction ({APPROVAL_THRESHOLD}) : action bloquee."
    if tier == RiskTier.automatic:
        return (
            f"Score de risque ({score:.2f}) au plus egal au seuil automatique ({AUTOMATIC_THRESHOLD}) "
            "et action non marquee comme sensible : execution immediate sans validation humaine."
        )
    if rating.sensitive:
        return (
            f"Action marquee comme sensible (sensitive=True) : validation humaine obligatoire meme si "
            f"le score de risque ({score:.2f}) est faible."
        )
    return f"Score de risque ({score:.2f}) superieur au seuil automatique ({AUTOMATIC_THRESHOLD}) : validation humaine requise avant execution."


@router.get("", response_model=list[ToolOut])
def list_tools(
    user: User = Depends(require_role(UserRole.admin, UserRole.pentester, UserRole.reader)),
):
    tools = []
    for tool_key, tool_info in TOOLS.items():
        profiles = []
        for profile_key, profile_info in tool_info["profiles"].items():
            try:
                score, tier, rating = classify_action(tool_key, profile_key)
            except UnknownActionRatingError:
                continue

            profiles.append(
                {
                    "profile": profile_key,
                    "label": profile_info["label"],
                    "explanation": profile_info["explanation"],
                    "risk": {
                        "impact": rating.impact,
                        "detectability": rating.detectability,
                        "reversibility": rating.reversibility,
                        "sensitive": rating.sensitive,
                        "score": score,
                        "tier": tier.value,
                        "tier_reason": _tier_reason(rating, score, tier),
                    },
                }
            )

        tools.append(
            {
                "tool": tool_key,
                "label": tool_info["label"],
                "what_is": tool_info["what_is"],
                "how_it_works": tool_info["how_it_works"],
                "example_finding": tool_info["example_finding"],
                "profiles": profiles,
            }
        )

    return tools
