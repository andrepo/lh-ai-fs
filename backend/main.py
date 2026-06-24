from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from agents import extractor_agent, legal_verifier_agent, factual_verifier_agent, synthesizer_agent
from langchain_core.runnables import RunnableParallel, RunnableLambda

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


# ---------------------------------------------------------
# LANGCHAIN ORCHESTRATION & FALLBACKS
# ---------------------------------------------------------
extractor_runnable = RunnableLambda(lambda inputs: extractor_agent(inputs["msj_text"]))


def run_factual_verifier_with_fallbacks(inputs):
    factual_assertions = [item for item in inputs["extracted_items"] if item.get("category") == "factual_assertion"]
    if not factual_assertions:
        return []
    try:
        return factual_verifier_agent(factual_assertions, inputs["source_docs"])
    except Exception as e:
        print(f"Factual verifier error: {e}")
        # Fallback return structure in case of agent errors
        return [{
            "id": claim.get("id"),
            "statement": claim.get("statement"),
            "status": "could_not_verify",
            "confidence": 0.0,
            "confidence_explanation": f"Factual verification failed due to system error: {str(e)}",
            "evidence": None,
            "source_file": None,
            "explanation": f"System error running verification: {str(e)}"
        } for claim in factual_assertions]


def run_legal_verifier_with_fallbacks(inputs):
    legal_citations = [item for item in inputs["extracted_items"] if item.get("category") == "legal_citation"]
    if not legal_citations:
        return []
    try:
        return legal_verifier_agent(legal_citations)
    except Exception as e:
        print(f"Legal verifier error: {e}")
        # Fallback return structure in case of agent errors
        return [{
            "id": claim.get("id"),
            "citation_target": claim.get("citation_target"),
            "statement": claim.get("statement"),
            "status": "unverified",
            "quote_accuracy": "no_quote",
            "actual_holding": None,
            "explanation": f"Legal verification failed due to system error: {str(e)}",
            "confidence": 0.0,
            "confidence_explanation": f"System error running verification: {str(e)}"
        } for claim in legal_citations]


# Define the overall LangChain orchestration pipeline
orchestrator_chain = (
    RunnableParallel(
        extracted_items=extractor_runnable,
        source_docs=RunnableLambda(lambda inputs: inputs["source_docs"])
    )
    | RunnableParallel(
        factual_results=RunnableLambda(run_factual_verifier_with_fallbacks),
        legal_results=RunnableLambda(run_legal_verifier_with_fallbacks)
    )
    | RunnableParallel(
        synthesis=RunnableLambda(lambda inputs: synthesizer_agent(inputs["factual_results"], inputs["legal_results"])),
        factual_verifications=RunnableLambda(lambda inputs: inputs["factual_results"]),
        legal_verifications=RunnableLambda(lambda inputs: inputs["legal_results"])
    )
)


@app.post("/analyze")
async def analyze():
    documents = load_documents()
    msj_text = documents.get("motion_for_summary_judgment", "")
    
    # Filter source documents (excluding the MSJ itself)
    source_docs = {
        k: v for k, v in documents.items() if k != "motion_for_summary_judgment"
    }
    
    # Run the coordinated LangChain pipeline
    inputs = {
        "msj_text": msj_text,
        "source_docs": source_docs
    }
    
    result = orchestrator_chain.invoke(inputs)
    synthesis = result["synthesis"]
    
    # Return structured JSON containing synthesis and specific verification lists
    return {
        "report": {
            "overall_confidence": synthesis.get("overall_confidence", 0.0),
            "summary": synthesis.get("summary", ""),
            "findings": synthesis.get("findings", []),
            "factual_verifications": result["factual_verifications"],
            "legal_verifications": result["legal_verifications"]
        }
    }



