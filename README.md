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

To power the `/filter` endpoint rapidly, the backend relies on an SQLite database (`papers.db`) that caches structured metadata natively extracted from your PDFs. 

Before querying the filter API, ensure you build or update the database:
```bash
uv run python update_db.py
```

**How it works:**
When you run `update_db.py`, the script scans the `papers/` directory for any PDF files. For each PDF, it does two things:
1. **Full-Text Extraction**: It uses the `pypdf` library to read through the actual text of the PDF locally on your machine. This full text is saved into the database, allowing you to perform deep keyword searches across the entire body of the paper (not just the title or abstract).
2. **Metadata Extraction via AI**: It sends the PDF to the Gemini API and asks the AI to read the document and cleanly extract over 20 specific attributes (like the *Cooling Rate*, *Preservation Method*, *Model Type*, etc.). The AI organizes this information into a strict, standardized format. 

All of this extracted information is saved into the `papers.db` SQLite file. When you query the `/filter` API later, it instantly searches this local database rather than having to re-read or re-process the PDFs, making your searches extremely fast and completely independent of the AI!

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
- `publication_type`, `model_type`, `research_type`, `funding_source`, `techniques`, `cpa_type`, `delivery_method`, `preservation_method`, `outcomes_metrics` (Array of Strings)
- `journal`, `author_institution`, `country_region` (String, partial matches)
- `cooling_rate` (Integer, °C/min), `warming_rate` (Integer, °C/min)
- `storage_duration` (Integer, days), `storage_temperature` (Integer, °C)
- `open_access` (boolean)
- `year_min`, `year_max` (integer ranges)
- `impact_factor_min`, `impact_factor_max` (float ranges)
- `citations_min`, `citations_max` (integer ranges)
- `cpa_concentration_min`, `cpa_concentration_max` (float ranges)

```bash
curl -X POST http://localhost:8000/filter \
  -H "Content-Type: application/json" \
  -d '{
        "keyword_search": "cryoprotection",
        "publication_type": ["Research Papers", "Review Papers"],
        "model_type": ["Cells", "Tissue slices"],
        "research_type": ["Basic", "Translational"],
        "journal": "Cryobiology",
        "open_access": true,
        "author_institution": "Stanford",
        "country_region": "USA",
        "funding_source": ["Government"],
        "techniques": ["Vitrification", "Laser warming"],
        "cpa_type": ["DMSO", "Glycerol"],
        "cpa_concentration_min": 5.0,
        "cpa_concentration_max": 15.5,
        "delivery_method": ["Bulk perfusion"],
        "preservation_method": ["Ice-free"],
        "outcomes_metrics": ["Post-thaw viability"],
        "cooling_rate": 1,
        "warming_rate": 50,
        "storage_duration": 180,
        "storage_temperature": -196,
        "year_min": 2020,
        "year_max": 2024,
        "impact_factor_min": 3.5,
        "impact_factor_max": 15.0,
        "citations_min": 5,
        "citations_max": 500
      }'
```

To retrieve **all** indexed papers simply provide an empty JSON payload, which tells the backend to strip all filters:

```bash
curl -X POST http://localhost:8000/filter \
  -H "Content-Type: application/json" \
  -d '{}'
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
