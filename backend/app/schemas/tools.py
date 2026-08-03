from pydantic import BaseModel


class ToolRiskOut(BaseModel):
    impact: int
    detectability: int
    reversibility: int
    sensitive: bool
    score: float
    tier: str
    tier_reason: str


class ToolProfileOut(BaseModel):
    profile: str
    label: str
    explanation: str
    risk: ToolRiskOut


class ToolFindingExampleOut(BaseModel):
    type: str
    description: str


class ToolOut(BaseModel):
    tool: str
    label: str
    what_is: str
    how_it_works: str
    example_finding: ToolFindingExampleOut
    profiles: list[ToolProfileOut]
