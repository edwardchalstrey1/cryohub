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
            print(
                f"Saved store {saved_name} not found or invalid. Creating a new one..."
            )

    if not store_name:
        print("Initializing new Gemini File Search Store...")
        # Create the store
        store = client.file_search_stores.create()
        store_name = store.name

        # Locate all PDFs in the papers/ directory
        papers_dir = os.path.join(os.path.dirname(__file__), "papers")
        pdf_files = glob.glob(os.path.join(papers_dir, "*.pdf"))

        print(f"Found {len(pdf_files)} PDF files in {papers_dir}. Uploading...")

        upload_ops = []
        for pdf_file in pdf_files:
            print(f"Uploading {os.path.basename(pdf_file)}...")
            op = client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store_name, file=pdf_file
            )
            upload_ops.append(op)

        print(
            "Waiting for files to be processed by Gemini (this may take a few moments)..."
        )
        for op in upload_ops:
            while not op.done:
                time.sleep(2)
                op = client.operations.get(op)

        # Save to file
        with open(store_file, "w") as f:
            f.write(store_name)

    # Save the references in global state so the endpoints can use them
    app_state["store_name"] = store_name
    app_state["client"] = client
    print(f"Store {store_name} is ready.")

    yield

    # Store persists across restarts for production, so no cleanup is performed here


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
            ],
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
            limitations=[],
        )

    return AskResponse(data=data, sources=sources)
