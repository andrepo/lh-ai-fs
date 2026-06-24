from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from agents import extractor_agent, legal_verifier_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS_DIR = Path(__file__).parent / "documents"


def load_documents() -> dict[str, str]:
    """Load all documents from the documents directory."""
    documents = {}
    for file_path in DOCUMENTS_DIR.glob("*.txt"):
        documents[file_path.stem] = file_path.read_text()
    return documents


@app.post("/analyze")
async def analyze():
    documents = load_documents()
    msj_text = documents.get("motion_for_summary_judgment", "")
    
    # Run the core multi-agent pipeline
    extracted_items = extractor_agent(msj_text)
    verified_items = legal_verifier_agent(extracted_items)
    
    return {"report": verified_items}

