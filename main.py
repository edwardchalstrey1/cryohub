import os
import glob
import time
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

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

    print("Initializing Gemini File Search Store...")
    # Create the store
    store = client.file_search_stores.create()

    # Locate all PDFs in the papers/ directory
    papers_dir = os.path.join(os.path.dirname(__file__), "papers")
    pdf_files = glob.glob(os.path.join(papers_dir, "*.pdf"))

    print(f"Found {len(pdf_files)} PDF files in {papers_dir}. Uploading...")

    upload_ops = []
    for pdf_file in pdf_files:
        print(f"Uploading {os.path.basename(pdf_file)}...")
        op = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store.name, file=pdf_file
        )
        upload_ops.append(op)

    print(
        "Waiting for files to be processed by Gemini (this may take a few moments)..."
    )
    for op in upload_ops:
        while not op.done:
            time.sleep(2)
            op = client.operations.get(op)

    # Save the references in global state so the endpoints can use them
    app_state["store_name"] = store.name
    app_state["client"] = client
    print(f"Store {store.name} is ready.")

    yield

    # Cleanup: delete the store when the app shuts down so we don't accumulate stores during dev
    print(f"Cleaning up store {store.name}...")
    client.file_search_stores.delete(name=store.name)


app = FastAPI(lifespan=lifespan)


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
            response_schema=ResearchFinding,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(file_search_store_names=[store_name])
                )
            ]
        ),
    )

    grounding = response.candidates[0].grounding_metadata
    sources = []
    if grounding and grounding.grounding_chunks:
        # Extract unique sources titles from the grounding chunks
        sources = list(
            {
                c.retrieved_context.title
                for c in grounding.grounding_chunks
                if c.retrieved_context
            }
        )

    try:
        data = ResearchFinding.model_validate_json(response.text)
    except Exception:
        # Fallback if structure fails
        data = ResearchFinding(
            summary=response.text,
            key_findings=[],
            materials_and_methods=[],
            limitations=[]
        )

    return AskResponse(data=data, sources=sources)
