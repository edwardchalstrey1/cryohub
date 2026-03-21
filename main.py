import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types
from dotenv import load_dotenv
from schemas import AskRequest, AskResponse, ResearchFinding, SYSTEM_PROMPT

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
