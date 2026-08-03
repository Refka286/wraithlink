from pydantic import BaseModel


class SuggestionItem(BaseModel):
    tool: str
    reasoning: str
    priority: str


class SuggestionsOut(BaseModel):
    suggestions: list[SuggestionItem]
