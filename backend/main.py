from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from agents import extractor_agent, legal_verifier_agent, factual_verifier_agent

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
    
    # Run the extractor agent
    extracted_items = extractor_agent(msj_text)
    
    # Partition the extracted items by category
    factual_assertions = [item for item in extracted_items if item.get("category") == "factual_assertion"]
    legal_citations = [item for item in extracted_items if item.get("category") == "legal_citation"]
    
    # Verify legal citations (relying on LLM's internal legal knowledge)
    verified_legal = legal_verifier_agent(legal_citations)
    
    # Verify factual assertions (relying on worksite source documents)
    source_docs = {
        k: v for k, v in documents.items() if k != "motion_for_summary_judgment"
    }
    verified_factual = factual_verifier_agent(factual_assertions, source_docs)
    
    # Return structured JSON
    return {
        "report": {
            "factual_verifications": verified_factual,
            "legal_verifications": verified_legal
        }
    }



