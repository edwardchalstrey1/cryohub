import os
import glob
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

def initialize_store():
    # Initialize the Gemini client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Please check your .env file.")
        return

    client = genai.Client(api_key=api_key)
    store_file = os.path.join(os.path.dirname(__file__), ".store_id")

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

    print("Waiting for files to be processed by Gemini (this may take a few moments)...")
    for op in upload_ops:
        while not op.done:
            time.sleep(2)
            op = client.operations.get(op)

    # Save to file
    with open(store_file, "w") as f:
        f.write(store_name)
    
    print(f"\nSuccess! Store {store_name} has been initialized and saved to .store_id")

if __name__ == "__main__":
    initialize_store()
