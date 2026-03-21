import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from dotenv import load_dotenv
from schemas import (
    AskRequest,
    AskResponse,
    ResearchFinding,
    SYSTEM_PROMPT,
    FilterRequest,
    FilterResponse,
    PaperInfo,
)

load_dotenv()

# Global state for communicating with the Gemini File Search store
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the Gemini client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not set. Please check your .env file.",
        )

    client = genai.Client(api_key=api_key)

    store_file = os.path.join(os.path.dirname(__file__), ".store_id")
    store_name = None

    if os.path.exists(store_file):
        with open(store_file, "r") as f:
            saved_name = f.read().strip()
        try:
            # Verify the store still exists
            client.file_search_stores.get(name=saved_name)
            store_name = saved_name
            print(f"Loaded existing Gemini File Search Store: {store_name}")
        except Exception:
            raise RuntimeError(
                f"Saved store {saved_name} not found or invalid. Please run init_store.py again."
            )
    else:
        raise RuntimeError(
            "File store not initialized. Please run 'uv run python init_store.py' before starting the server."
        )

    # Save the references in global state so the endpoints can use them
    app_state["store_name"] = store_name
    app_state["client"] = client
    print(f"Store {store_name} is ready.")

    yield

    # Store persists across restarts for production, so no cleanup is performed here


app = FastAPI(lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    client = app_state.get("client")
    store_name = app_state.get("store_name")

    if not client or not store_name:
        raise HTTPException(
            status_code=503,
            detail="The File Search store is not fully initialized. Please try again in a few seconds.",
        )

    response = client.models.generate_content(
        model=req.model,
        contents=req.prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=SYSTEM_PROMPT,
            response_schema=ResearchFinding,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(file_search_store_names=[store_name])
                )
            ],
        ),
    )

    try:
        data = ResearchFinding.model_validate_json(response.text)
    except Exception:
        # Fallback if structure fails
        data = ResearchFinding(
            summary=response.text,
            key_findings=[],
            materials_and_methods=[],
            limitations=[],
            sources=[],
            dois=[],
        )

    return AskResponse(data=data, sources=data.sources, dois=data.dois)


@app.post("/filter", response_model=FilterResponse)
def filter_papers(req: FilterRequest):
    import sqlite3
    import json
    
    db_path = os.path.join(os.path.dirname(__file__), "papers.db")
    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=500, 
            detail="Database not found. Please run 'python update_db.py' first."
        )
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM papers WHERE 1=1"
    params = []

    if req.year_min is not None:
        query += " AND publication_year >= ?"
        params.append(req.year_min)
    if req.year_max is not None:
        query += " AND publication_year <= ?"
        params.append(req.year_max)
    if req.impact_factor_min is not None:
        query += " AND journal_impact_factor >= ?"
        params.append(req.impact_factor_min)
    if req.impact_factor_max is not None:
        query += " AND journal_impact_factor <= ?"
        params.append(req.impact_factor_max)
    if req.citations_min is not None:
        query += " AND citations >= ?"
        params.append(req.citations_min)
    if req.citations_max is not None:
        query += " AND citations <= ?"
        params.append(req.citations_max)
        
    if req.journal:
        query += " AND journal LIKE ?"
        params.append(f"%{req.journal}%")
    if req.author_institution:
        query += " AND author_institution LIKE ?"
        params.append(f"%{req.author_institution}%")
    if req.country_region:
        query += " AND country_region LIKE ?"
        params.append(f"%{req.country_region}%")
        
    if req.open_access is True:
        query += " AND open_access = 1"
    elif req.open_access is False:
        query += " AND open_access = 0"

    if req.publication_type:
        for pt in req.publication_type:
            query += " AND publication_type LIKE ?"
            params.append(f'%"{pt}"%')
    if req.model_systems:
        for ms in req.model_systems:
            query += " AND model_systems LIKE ?"
            params.append(f'%"{ms}"%')
    if req.research_type:
        for rt in req.research_type:
            query += " AND research_type LIKE ?"
            params.append(f'%"{rt}"%')
    if req.funding_source:
        for fs in req.funding_source:
            query += " AND funding_source LIKE ?"
            params.append(f'%"{fs}"%')
    if req.techniques:
        for tech in req.techniques:
            query += " AND techniques LIKE ?"
            params.append(f'%"{tech}"%')

    if req.keyword_search:
        query += " AND (title LIKE ? OR abstract LIKE ? OR full_text LIKE ?)"
        params.extend([f"%{req.keyword_search}%", f"%{req.keyword_search}%", f"%{req.keyword_search}%"])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    papers = []
    for row in rows:
        papers.append(
            PaperInfo(
                title=row["title"],
                abstract=row["abstract"],
                authors=json.loads(row["authors"]) if row["authors"] else [],
                publication_year=row["publication_year"],
                journal=row["journal"],
                open_access=bool(row["open_access"]),
                url_or_doi=row["url_or_doi"],
                publication_type=json.loads(row["publication_type"]) if row["publication_type"] else [],
                model_systems=json.loads(row["model_systems"]) if row["model_systems"] else [],
                research_type=json.loads(row["research_type"]) if row["research_type"] else [],
                journal_impact_factor=row["journal_impact_factor"],
                author_institution=json.loads(row["author_institution"]) if row["author_institution"] else [],
                country_region=json.loads(row["country_region"]) if row["country_region"] else [],
                funding_source=json.loads(row["funding_source"]) if row["funding_source"] else [],
                citations=row["citations"],
                techniques=json.loads(row["techniques"]) if row["techniques"] else []
            )
        )
        
    conn.close()
    return FilterResponse(papers=papers)
