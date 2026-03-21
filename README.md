# Cryohub
A Knowledge Engine for the Cryonics, Cryopreservation, and Cryobiology research communities

This repo contains the backend.

## Challenge

Answer questions such as:

- "What CPAs have the lowest toxicity at vitrification concentrations for neural tissue?"
- "What is the current state of evidence on long-term potentiation recovery post-vitrification?"

... and get a grounded, cited answer — not a hallucination. 

## Setup

### Prerequisites
*   [uv](https://docs.astral.sh/uv/) (for fast Python environment management)
*   Python 3.10+
*   A Gemini API key (`GEMINI_API_KEY` environment variable)

### Installation

1.  Create a virtual environment with `uv`:
    ```bash
    uv venv
    ```
2.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    uv pip install -r requirements.txt
    ```
4.  Set up your environment variables by creating a `.env` file in the root directory:
    ```bash
    echo "GEMINI_API_KEY=your-api-key-here" > .env
    ```

### Running the Backend

Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The server will automatically fetch the PDFs from the `papers/` directory, create a Gemini File Search store, upload them, and wait for them to finish processing before accepting requests.

### Testing the API

Once the server says "Store is ready", you can query it:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What CPAs have the lowest toxicity at vitrification concentrations for neural tissue?"}'
```
