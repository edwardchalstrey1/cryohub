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

class PaperInfo(BaseModel):
    title: str
    abstract: str
    authors: list[str]
    publication_year: int | None = None
    journal: str | None = None
    open_access: bool
    url_or_doi: str | None = None

    # Comprehensive Filters
    publication_type: list[str]
    model_type: list[str]
    research_type: list[str]
    journal_impact_factor: float | None = None
    author_institution: list[str]
    country_region: list[str]
    funding_source: list[str]
    citations: int | None = None
    techniques: list[str]
    
    # Newly added fields from screenshot 2
    cpa_type: list[str]
    cpa_concentration: str | None = None
    delivery_method: list[str]
    preservation_method: list[str]
    outcomes_metrics: list[str]
    cooling_rate: str | None = None
    warming_rate: str | None = None
    storage_duration: str | None = None
    storage_temperature: str | None = None

class FilterRequest(BaseModel):
    keyword_search: str | None = None

    # Text / Enum Matches
    publication_type: list[str] | None = None
    model_type: list[str] | None = None
    research_type: list[str] | None = None
    journal: str | None = None
    open_access: bool | None = None
    author_institution: str | None = None
    country_region: str | None = None
    funding_source: list[str] | None = None
    techniques: list[str] | None = None

    cpa_type: list[str] | None = None
    cpa_concentration: str | None = None
    delivery_method: list[str] | None = None
    preservation_method: list[str] | None = None
    outcomes_metrics: list[str] | None = None
    cooling_rate: str | None = None
    warming_rate: str | None = None
    storage_duration: str | None = None
    storage_temperature: str | None = None

    # Ranges
    year_min: int | None = None
    year_max: int | None = None
    impact_factor_min: float | None = None
    impact_factor_max: float | None = None
    citations_min: int | None = None
    citations_max: int | None = None

    model: Literal["gemini-flash-latest", "gemini-pro-latest"] = "gemini-flash-latest"


class FilterResponse(BaseModel):
    papers: list[PaperInfo]
