from pydantic import BaseModel
from typing import Literal

ResearchTypeEnum = Literal["Basic", "Preclinical", "Clinical", "Computational"]
FundingSourceEnum = Literal["Industry", "Academia", "Government"]

TechniquesEnum = Literal[
    "Freezing",
    "Vitrification",
    "Slow Freezing",
    "Rapid Freezing",
    "Directional Freezing",
    "Ice-seeding",
    "Rewarming",
    "Convective warming",
    "Laser warming",
    "Nanowarming",
    "Microwave warming",
]

DeliveryEnum = Literal[
    "Bulk perfusion",
    "Vascular perfusion",
    "Machine perfusion",
    "Stepwise CPA loading",
    "Single-step CPA loading",
]

PreservationEnum = Literal[
    "Ice-based", "Ice-free", "Supercooling", "Isochoric preservation"
]

OutcomesEnum = Literal[
    "Post-thaw viability",
    "Functional recovery",
    "Structural integrity",
    "Long-term survival",
    "Fertilization success",
]

PublicationTypeEnum = Literal[
    "Research Papers",
    "Methods Papers",
    "Review Papers",
    "Meta Analyses",
    "Protocols",
    "Guidelines",
    "Academic Theses",
    "Patents",
    "Preprints",
    "Conference Proceedings",
    "Technical Reports",
    "Grey Literature",
]

ModelTypeEnum = Literal[
    "Cells",
    "Cell lines",
    "Primary cells",
    "Reproductive cells",
    "Stem cells",
    "Immune cells",
    "Cancer cells",
    "Tissues & 3D Models",
    "Tissue slices & Biopsies",
    "Organoids",
    "Engineered tissues",
    "Whole Organ Models",
    "Kidneys",
    "Livers",
    "Hearts",
    "Lungs",
    "Model Organisms",
    "Extremophiles",
    "Invertebrates",
    "Fish",
    "Amphibians",
    "Rodents",
    "Livestock",
    "Non-human primates",
    "Humans",
]


# 1. Define the Output Structure (Pydantic)
# This ensures structured data for the dashboard.
class AskRequest(BaseModel):
    prompt: str
    model: Literal["gemini-flash-latest", "gemini-pro-latest"] = "gemini-flash-latest"


class ResearchFinding(BaseModel):
    summary: str
    key_findings: list[str]
    limitations: list[str]
    source_titles: list[str]


class AskResponse(BaseModel):
    data: ResearchFinding
    sources: list[dict]


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
Be objective, cite your sources via exact paper titles to allow database lookup.
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
    publication_type: list[PublicationTypeEnum]
    model_type: list[ModelTypeEnum]
    research_type: list[ResearchTypeEnum]
    journal_impact_factor: float | None = None
    author_institution: list[str]
    country_region: list[str]
    funding_source: list[FundingSourceEnum]
    citations: int | None = None
    techniques: list[TechniquesEnum]
    cpa_type: list[str]
    cpa_concentration_min: float | None = None
    cpa_concentration_max: float | None = None
    delivery_method: list[DeliveryEnum]
    preservation_method: list[PreservationEnum]
    outcomes_metrics: list[OutcomesEnum]
    cooling_rate: int | None = None
    warming_rate: int | None = None
    storage_duration: int | None = None
    storage_temperature: int | None = None


class FilterRequest(BaseModel):
    keyword_search: str | None = None

    publication_type: list[PublicationTypeEnum] | None = None
    model_type: list[ModelTypeEnum] | None = None
    research_type: list[ResearchTypeEnum] | None = None
    journal: str | None = None
    open_access: bool | None = None
    author_institution: str | None = None
    country_region: str | None = None
    funding_source: list[FundingSourceEnum] | None = None
    techniques: list[TechniquesEnum] | None = None

    cpa_type: list[str] | None = None
    cpa_concentration_min: float | None = None
    cpa_concentration_max: float | None = None
    delivery_method: list[DeliveryEnum] | None = None
    preservation_method: list[PreservationEnum] | None = None
    outcomes_metrics: list[OutcomesEnum] | None = None
    cooling_rate: int | None = None
    warming_rate: int | None = None
    storage_duration: int | None = None
    storage_temperature: int | None = None

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
