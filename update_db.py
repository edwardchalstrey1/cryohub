import os
import glob
import sqlite3
import json
import pypdf
from google import genai
from google.genai import types
from dotenv import load_dotenv
from schemas import PaperInfo

load_dotenv()

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS papers")
    cursor.execute('''
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            title TEXT,
            abstract TEXT,
            authors TEXT,
            publication_year INTEGER,
            journal TEXT,
            open_access INTEGER,
            url_or_doi TEXT,
            full_text TEXT,
            
            publication_type TEXT,
            model_type TEXT,
            research_type TEXT,
            journal_impact_factor REAL,
            author_institution TEXT,
            country_region TEXT,
            funding_source TEXT,
            citations INTEGER,
            techniques TEXT,
            
            cpa_type TEXT,
            cpa_concentration TEXT,
            delivery_method TEXT,
            preservation_method TEXT,
            outcomes_metrics TEXT,
            cooling_rate TEXT,
            warming_rate TEXT,
            storage_duration TEXT,
            storage_temperature TEXT
        )
    ''')
    conn.commit()

def update_database():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Please check your .env file.")
        return

    client = genai.Client(api_key=api_key)
    conn = sqlite3.connect("papers.db")
    init_db(conn)
    cursor = conn.cursor()

    papers_dir = os.path.join(os.path.dirname(__file__), "papers")
    pdf_files = glob.glob(os.path.join(papers_dir, "*.pdf"))

    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        
        # Local text extraction
        full_text = ""
        try:
            with open(pdf_file, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    full_text += (page.extract_text() or "") + "\n"
        except Exception as e:
            print(f"Failed to extract text locally for {filename}: {e}")
            
        print(f"Processing {filename} via Gemini...")
        
        try:
            uploaded_file = client.files.upload(file=pdf_file)
        except Exception as e:
            print(f"Failed to upload {filename}: {e}")
            continue
            
        prompt = (
            "Extract the explicit detailed metadata for this research paper according to the comprehensive PaperInfo schema. "
            "For arrays like publication_type, model_type, or techniques, cross-reference against standard scientific classifications. "
            "For arrays like cpa_type and delivery_method, categorize cleanly based on explicitly stated cryoprotective methods. "
            "For journal impact factor and citations, ONLY extract them if explicitly stated in the text, otherwise return null. "
            "For cooling_rate, warming_rate, storage_duration, and storage_temperature, extract the explicit values as strings if present. "
            "If open access status is not stated cleanly, infer based on copyright block or return false."
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PaperInfo,
                )
            )
            
            data = PaperInfo.model_validate_json(response.text)
            
            cursor.execute('''
                INSERT INTO papers (
                    filename, title, abstract, authors, publication_year, journal, open_access, url_or_doi, full_text,
                    publication_type, model_type, research_type, journal_impact_factor, author_institution, country_region, funding_source, citations, techniques,
                    cpa_type, cpa_concentration, delivery_method, preservation_method, outcomes_metrics, cooling_rate, warming_rate, storage_duration, storage_temperature
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename, 
                data.title, 
                data.abstract, 
                json.dumps(data.authors), 
                data.publication_year, 
                data.journal, 
                1 if data.open_access else 0, 
                data.url_or_doi,
                full_text,
                json.dumps(data.publication_type),
                json.dumps(data.model_type),
                json.dumps(data.research_type),
                data.journal_impact_factor,
                json.dumps(data.author_institution),
                json.dumps(data.country_region),
                json.dumps(data.funding_source),
                data.citations,
                json.dumps(data.techniques),
                json.dumps(data.cpa_type),
                data.cpa_concentration,
                json.dumps(data.delivery_method),
                json.dumps(data.preservation_method),
                json.dumps(data.outcomes_metrics),
                data.cooling_rate,
                data.warming_rate,
                data.storage_duration,
                data.storage_temperature
            ))
            conn.commit()
            print(f"Successfully added {filename} to database.")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")

    conn.close()
    print("\nDatabase update complete. 'papers.db' is ready for querying!")

if __name__ == "__main__":
    update_database()
