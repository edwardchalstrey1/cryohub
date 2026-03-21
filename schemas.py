from pydantic import BaseModel
from typing import Literal


# 1. Define the Output Structure (Pydantic)
# This ensures structured data for the dashboard.
class AskRequest(BaseModel):
    prompt: str
    model: Literal["gemini-flash-latest", "gemini-pro-latest"] = "gemini-flash-latest"


class ResearchFinding(BaseModel):
    summary: str
    key_findings: list[str]
    materials_and_methods: list[str]
    limitations: list[str]
    sources: list[str]
    dois: list[str]


class AskResponse(BaseModel):
    data: ResearchFinding
    sources: list[str]
    dois: list[str]


# 2. Define the Agent's "System Prompt"
SYSTEM_PROMPT = """
You are a Knowledge Engine for the Cryonics, Cryopreservation, and Cryobiology research communities.
Your goal is to answer questions about the latest scientific literature in these fields.

You will be provided with a question.
You must:
1. Search for any and all literature provided relating to the question.
2. Analyze and summarize literature.
3. Provide a structured report.

Always return structured results that match the ResearchFinding schema.
Be objective, cite your sources via paper titles and DOIs.
"""
