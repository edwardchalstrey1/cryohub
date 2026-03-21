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
    deactivate
    ```
4.  Set up your environment variables by creating a `.env` file in the root directory:
    ```bash
    echo "GEMINI_API_KEY=your-api-key-here" > .env
    ```

### Initialize the File Store

First, initialize the file store. This only needs to be run once in advance of querying the API (or whenever you add new PDFs to the `papers/` directory):
```bash
uv run python init_store.py
```

### Database Initialization

To power the `/filter` endpoint rapidly, the backend relies on an SQLite database that caches structured metadata natively extracted from your PDFs. 

Before querying the filter API, ensure you build or update the database:
```bash
uv run python update_db.py
```
This script will seamlessly parse all documents in `papers/` and save their `PaperInfo` attributes locally to `papers.db`.

### Running the Backend

Then, start the FastAPI server:
```bash
uv run uvicorn main:app --reload
```

The server will automatically attach to the existing File Search store configured by the initialization script, avoiding redundant upload times.

## Testing the API

### Asking Questions

Once the server says "Store is ready", you can query it:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What CPAs have the lowest toxicity at vitrification concentrations for neural tissue?"}'
```

#### Example Response

The backend enforces a strict JSON schema and returns the extracted `data` along with the grounding `sources` used:

```json
{
  "data": {
    "summary": "According to the literature, M22 and variations of VSN22 show reduced toxicity...",
    "key_findings": [
      "M22 achieves vitrification with acceptable viability in cortical slices.",
      "Toxicity is primarily driven by osmotic stress rather than biochemical toxicity at -130°C."
    ],
    "materials_and_methods": [
      "M22 (Cryoprotective Agent)",
      "Neural Cortical Slices",
      "Vitrification"
    ],
    "limitations": [
      "Long-term structural connectivity recovery remains unproven."
    ]
  },
  "sources": [
    "Advances in Neural Cryopreservation - Smith et al."
  ],
  "dois": [
    "10.1016/j.cryobiol.2023.123456"
  ]
}
```


### Filtering Papers

You can use the `/filter` endpoint to rapidly and locally query your `papers.db` corpus using highly specific metadata constraints and general keywords. 

### Available Filter Fields
- `keyword_search` (string)
- `publication_type`, `model_systems`, `research_type`, `funding_source`, `techniques` (Array of Strings)
- `journal`, `author_institution`, `country_region` (String, partial matches)
- `open_access` (boolean)
- `year_min`, `year_max` (integer ranges)
- `impact_factor_min`, `impact_factor_max` (float ranges)
- `citations_min`, `citations_max` (integer ranges)

```bash
curl -X POST http://localhost:8000/filter \
  -H "Content-Type: application/json" \
  -d '{
        "year_min": 2020,
        "year_max": 2024,
        "open_access": true,
        "keyword_search": "cryoprotection",
        "model_systems": ["Cells"],
        "impact_factor_min": 3.5
      }'
```

The backend dynamically structures this query and returns a strictly typed `PaperInfo` grouping of every document that fulfills your request:

```json
{
  "papers": [
    {
      "title": "Advances in Neural Cryopreservation",
      "abstract": "This study examines the impacts of...",
      "authors": ["Smith A.", "Jones B."],
      "publication_year": "2023",
      "journal": "Cryobiology",
      "open_access": true,
      "url_or_doi": "10.1016/j.cryobiol.2023.123456"
    }
  ]
}
```
