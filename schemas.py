from pydantic import BaseModel
from typing import Literal


class AskRequest(BaseModel):
    prompt: str
    model: Literal["gemini-flash-latest", "gemini-pro-latest"] = "gemini-flash-latest"


class ResearchFinding(BaseModel):
    summary: str
    key_findings: list[str]
    materials_and_methods: list[str]
    limitations: list[str]


class AskResponse(BaseModel):
    data: ResearchFinding
    sources: list[str]
