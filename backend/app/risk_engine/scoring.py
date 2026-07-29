from dataclasses import dataclass


@dataclass(frozen=True)
class RiskRating:
    impact: int
    detectability: int
    reversibility: int
    sensitive: bool = False

    def __post_init__(self):
        for name, value in (
            ("impact", self.impact),
            ("detectability", self.detectability),
            ("reversibility", self.reversibility),
        ):
            if not 1 <= value <= 5:
                raise ValueError(f"{name} must be between 1 and 5, got {value}")


def compute_score(rating: RiskRating) -> float:
    return rating.impact * rating.detectability / rating.reversibility
