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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            title TEXT,
            abstract TEXT,
            authors TEXT,
            publication_year TEXT,
            journal TEXT,
            open_access INTEGER,
            url_or_doi TEXT,
            full_text TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE papers ADD COLUMN full_text TEXT")
    except sqlite3.OperationalError:
        pass
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
        
        cursor.execute("SELECT full_text FROM papers WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        
        # Local text extraction
        full_text = ""
        try:
            with open(pdf_file, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    full_text += (page.extract_text() or "") + "\n"
        except Exception as e:
            print(f"Failed to extract text locally for {filename}: {e}")

        if row:
            if row[0]:
                print(f"Skipping {filename}, already fully processed.")
                continue
            else:
                print(f"Updating {filename} with full text...")
                cursor.execute("UPDATE papers SET full_text = ? WHERE filename = ?", (full_text, filename))
                conn.commit()
                continue
            
        print(f"Processing {filename} via Gemini...")
        
        try:
            uploaded_file = client.files.upload(file=pdf_file)
        except Exception as e:
            print(f"Failed to upload {filename}: {e}")
            continue
            
        prompt = "Extract the explicit detailed metadata for this research paper. If open access status is not stated cleanly, infer based on copyright block or return false."
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
                INSERT INTO papers (filename, title, abstract, authors, publication_year, journal, open_access, url_or_doi, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename, 
                data.title, 
                data.abstract, 
                json.dumps(data.authors), 
                data.publication_year, 
                data.journal, 
                1 if data.open_access else 0, 
                data.url_or_doi,
                full_text
            ))
            conn.commit()
            print(f"Successfully added {filename} to database.")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")

    conn.close()
    print("\nDatabase update complete. 'papers.db' is ready for querying!")

if __name__ == "__main__":
    update_database()
