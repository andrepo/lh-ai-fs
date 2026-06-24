import sys
import subprocess
from pathlib import Path

# Auto-execute inside the virtual environment if not already running in it
current_dir = Path(__file__).parent.resolve()
venv_python = current_dir / "venv" / "bin" / "python"
if not venv_python.exists():
    venv_python = current_dir / "venv" / "Scripts" / "python.exe"

venv_dir = current_dir / "venv"
if venv_python.exists() and Path(sys.prefix).resolve() != venv_dir.resolve():
    cmd = [str(venv_python)] + sys.argv
    sys.exit(subprocess.call(cmd))

import json

# Ensure backend path is in sys.path
sys.path.append(str(current_dir))

from main import load_documents
from agents import extractor_agent, legal_verifier_agent, factual_verifier_agent

# ---------------------------------------------------------
# NORMALIZATION UTILITIES
# ---------------------------------------------------------
def normalize_status(status: str) -> str:
    """Normalizes status string to a canonical format."""
    if not status:
        return ""
    status_lower = status.lower().strip()
    if status_lower in ["could_not_verify", "could not verify", "unverified", "not verified"]:
        return "could_not_verify"
    if status_lower in ["mischaracterized", "misrepresented", "manipulated"]:
        return "mischaracterized"
    return status_lower


def normalize_filename(filename: str) -> str:
    """Strips paths and extensions to normalize file references."""
    if not filename:
        return ""
    return Path(filename).stem.lower().strip()


# ---------------------------------------------------------
# GROUND TRUTH DEFINITIONS
# ---------------------------------------------------------
# Each entry defines:
# - match_keywords: specific phrases to prevent substring collisions
# - type: "legal" or "factual"
# - expected_statuses: list of correct/acceptable status values
# - description: user-friendly label

GROUND_TRUTH = {
    # Legal Citations
    "Privette": {
        "type": "legal",
        "match_keywords": ["privette"],
        "pinpoints": {
            "695": {
                "expected_statuses": ["supported"],
                "description": "Privette v. Superior Court (p. 695) - presumptive non-liability"
            },
            "702": {
                "expected_statuses": ["mischaracterized", "contradicted"],
                "description": "Privette v. Superior Court (p. 702) - 'never liable' quote manipulation"
            }
        }
    },
    "Whitmore": {
        "type": "legal",
        "match_keywords": ["whitmore"],
        "expected_statuses": ["fabricated"],
        "description": "Whitmore v. Delgado Scaffolding Co. - fabricated case"
    },
    "Kellerman": {
        "type": "legal",
        "match_keywords": ["kellerman"],
        "expected_statuses": ["fabricated"],
        "description": "Kellerman v. Pacific Coast Construction, Inc. - fabricated case"
    },
    "Seabright": {
        "type": "legal",
        "match_keywords": ["seabright"],
        "expected_statuses": ["supported"],
        "description": "Seabright Insurance Co. v. US Airways, Inc. - delegation of safety duty"
    },
    "335.1": {
        "type": "legal",
        "match_keywords": ["335.1", "section 335.1"],
        "expected_statuses": ["supported"],
        "description": "CCP Section 335.1 - two-year statute of limitations"
    },
    "Torres": {
        "type": "legal",
        "match_keywords": ["torres"],
        "expected_statuses": ["mischaracterized", "fabricated", "could_not_verify", "unverified"],
        "description": "Torres v. Granite Falls Dev. Corp. - footnote case mischaracterized/fabricated"
    },
    "Blackwell": {
        "type": "legal",
        "match_keywords": ["blackwell"],
        "expected_statuses": ["mischaracterized", "fabricated", "could_not_verify", "unverified"],
        "description": "Blackwell v. Sunrise Contractors - footnote case mischaracterized/fabricated"
    },
    "Dixon": {
        "type": "legal",
        "match_keywords": ["dixon"],
        "expected_statuses": ["mischaracterized", "could_not_verify", "unverified"],
        "description": "Dixon v. Lone Star Structural - footnote case (out-of-state) mischaracterized/unverified"
    },
    "Okafor": {
        "type": "legal",
        "match_keywords": ["okafor"],
        "expected_statuses": ["mischaracterized", "could_not_verify", "unverified"],
        "description": "Okafor v. Brightline Builders - footnote case (out-of-state) mischaracterized/unverified"
    },
    "Nguyen": {
        "type": "legal",
        "match_keywords": ["nguyen"],
        "expected_statuses": ["mischaracterized", "fabricated", "could_not_verify", "unverified"],
        "description": "Nguyen v. Allied Pacific Construction - footnote case mischaracterized/fabricated"
    },
    "Reeves": {
        "type": "legal",
        "match_keywords": ["reeves"],
        "expected_statuses": ["mischaracterized", "fabricated", "could_not_verify", "unverified"],
        "description": "Reeves v. Summit Engineering Group - footnote case mischaracterized/fabricated"
    },

    # Factual Assertions
    "general contractor": {
        "type": "factual",
        "match_keywords": ["general contractor", "harmon served as"],
        "expected_statuses": ["supported"],
        "description": "Factual Claim: Harmon served as general contractor"
    },
    "employed": {
        "type": "factual",
        "match_keywords": ["employed by apex", "employee of apex", "employed by subcontractor apex"],
        "expected_statuses": ["supported"],
        "description": "Factual Claim: Rivera was employed by Apex"
    },
    "March 14": {
        "type": "factual",
        "match_keywords": ["march 14", "occurred on march 14", "incident was on march 14"],
        "expected_statuses": ["contradicted"],
        "description": "Factual Claim: Incident occurred on March 14, 2021 (Actual: March 12)"
    },
    "wearing": {
        "type": "factual",
        "match_keywords": ["not wearing", "wearing required", "wearing personal", "protective equipment", "safety harness", "fall-arrest"],
        "expected_statuses": ["contradicted"],
        "description": "Factual Claim: Rivera was not wearing required PPE (Actual: was wearing)"
    },
    "February 26": {
        "type": "factual",
        "match_keywords": ["february 26", "feb 26", "most recent being february 26"],
        "expected_statuses": ["could_not_verify"],
        "description": "Factual Claim: OSHA inspection occurred on Feb 26, 2021 (Actual: no inspection records present)"
    },
    "March 10, 2023": {
        "type": "factual",
        "match_keywords": ["march 10, 2023", "filed the instant", "filed his complaint until"],
        "expected_statuses": ["could_not_verify"],
        "description": "Factual Claim: Rivera filed action on March 10, 2023 (Actual: no filing records in source docs)"
    }
}

def find_ground_truth_key(item: dict) -> tuple:
    """Matches a pipeline item to a ground truth key and resolves expected statuses."""
    statement = item.get("statement", "")
    statement = statement.lower() if statement else ""
    
    citation_target = item.get("citation_target", "")
    citation_target = citation_target.lower() if citation_target else ""
    
    # Handle Legal Citations first (anything with a citation target)
    if citation_target:
        # Handle Privette pinpoints specifically
        if "privette" in citation_target:
            pinpoint = "702" if ("702" in citation_target or "never" in statement) else "695"
            gt_info = GROUND_TRUTH["Privette"]["pinpoints"][pinpoint]
            return "Privette_" + pinpoint, gt_info

        for key, value in GROUND_TRUTH.items():
            if value["type"] == "legal" and key != "Privette":
                # Check match keywords to prevent collisions
                for kw in value.get("match_keywords", []):
                    if kw.lower() in citation_target:
                        return key, value

    # Handle Factual Assertions (no citation target)
    else:
        for key, value in GROUND_TRUTH.items():
            if value["type"] == "factual":
                # Check match keywords strictly in the statement text
                for kw in value.get("match_keywords", []):
                    if kw.lower() in statement:
                        return key, value

    return None, None

def run_evaluations():
    print("=" * 60)
    print("      RUNNING BS DETECTOR PIPELINE EVALUATION HARNESS")
    print("=" * 60)
    
    # Load docs
    documents = load_documents()
    msj_text = documents.get("motion_for_summary_judgment", "")
    source_docs = {k: v for k, v in documents.items() if k != "motion_for_summary_judgment"}
    
    print("\n[1/3] Running Extractor Agent...")
    extracted_items = extractor_agent(msj_text)
    print(f"      Extracted {len(extracted_items)} items total.")
    
    # Partition
    factual_assertions = [item for item in extracted_items if item.get("category") == "factual_assertion"]
    legal_citations = [item for item in extracted_items if item.get("category") == "legal_citation"]
    
    print("[2/3] Running Verifier Agents...")
    verified_legal = legal_verifier_agent(legal_citations)
    verified_factual = factual_verifier_agent(factual_assertions, source_docs)
    pipeline_results = verified_legal + verified_factual
    print(f"      Verified {len(pipeline_results)} items.")
    
    print("\n[3/3] Analyzing Pipeline Accuracy vs. Ground Truth...")
    
    tp_flaws = 0  # True positive flaws flagged (contradicted/fabricated/mischaracterized matches)
    fp_flaws = 0  # False positive flaws flagged (pipeline flagged supported as flaw, or hallucinated a flaw)
    fn_flaws = 0  # False negative flaws (actual flaw expected, but pipeline labeled supported or missed it)
    
    correct_assessments = 0
    total_processed = 0
    
    gt_checked = set()
    
    print("\nDetailed Comparisons:")
    print("-" * 60)
    
    # Map pipeline outputs to ground truth
    for item in pipeline_results:
        raw_status = item.get("status")
        status = normalize_status(raw_status)
        
        gt_key, gt_entry = find_ground_truth_key(item)
        print(f"DEBUG: id={item.get('id')}, target={item.get('citation_target')}, statement={item.get('statement', '')[:40]}... -> matched_key={gt_key}, status={status}")

        if not gt_key:
            # Pipeline processed an item we didn't specify in ground truth
            # We treat this as an extra check (neutral unless it's a hallucinated flaw)
            if status in ["contradicted", "fabricated", "mischaracterized"]:
                fp_flaws += 1
            total_processed += 1
            continue
            
        gt_checked.add(gt_key)
        expected_statuses = [normalize_status(s) for s in gt_entry["expected_statuses"]]
        description = gt_entry["description"]
        
        is_correct = (status in expected_statuses)
        if is_correct:
            correct_assessments += 1
        total_processed += 1
        
        # Refactored Precision/Recall categorization
        is_flaw_expected = any(s in ["contradicted", "fabricated", "mischaracterized"] for s in expected_statuses)
        is_flaw_flagged = status in ["contradicted", "fabricated", "mischaracterized"]
        
        if is_correct and is_flaw_flagged:
            tp_flaws += 1
            print(f"✓ [TP] {description}")
            print(f"      Expected (one of): {expected_statuses} | Got: {status} (Match)")
        elif is_correct and not is_flaw_flagged:
            # The model correctly chose a non-flaw status allowed by ground truth
            print(f"✓ [TN] {description}")
            print(f"      Expected (one of): {expected_statuses} | Got: {status}")
        elif not is_correct and is_flaw_flagged:
            fp_flaws += 1
            print(f"✗ [FP] {description}")
            print(f"      Expected (one of): {expected_statuses} | Got: {status} (False Alarm)")
        elif not is_correct and not is_flaw_flagged:
            fn_flaws += 1
            print(f"✗ [FN] {description}")
            print(f"      Expected (one of): {expected_statuses} | Got: {status} (Missed)")

    # Check for ground truth items that were completely missed by the pipeline
    for key, entry in GROUND_TRUTH.items():
        # Handle nested Privette keys
        if key == "Privette":
            for pin, pin_entry in entry["pinpoints"].items():
                full_pin_key = f"Privette_{pin}"
                if full_pin_key not in gt_checked:
                    expected_statuses = [normalize_status(s) for s in pin_entry["expected_statuses"]]
                    is_flaw_expected = any(s in ["contradicted", "fabricated", "mischaracterized"] for s in expected_statuses)
                    if is_flaw_expected:
                        fn_flaws += 1
                    print(f"✗ [FN] {pin_entry['description']} (Not extracted by pipeline)")
        elif key not in gt_checked:
            expected_statuses = [normalize_status(s) for s in entry["expected_statuses"]]
            is_flaw_expected = any(s in ["contradicted", "fabricated", "mischaracterized"] for s in expected_statuses)
            if is_flaw_expected:
                fn_flaws += 1
            print(f"✗ [FN] {entry['description']} (Not extracted by pipeline)")

    # Compute Metrics
    precision = tp_flaws / (tp_flaws + fp_flaws) if (tp_flaws + fp_flaws) > 0 else 1.0
    recall = tp_flaws / (tp_flaws + fn_flaws) if (tp_flaws + fn_flaws) > 0 else 1.0
    hallucination_rate = 1.0 - (correct_assessments / total_processed) if total_processed > 0 else 0.0
    
    print("\n" + "=" * 60)
    print("                  EVALUATION METRICS SUMMARY")
    print("=" * 60)
    print(f"  Total Processed Claims:       {total_processed}")
    print(f"  True Positives (Flaws found): {tp_flaws}")
    print(f"  False Positives (False alarms): {fp_flaws}")
    print(f"  False Negatives (Missed flaws): {fn_flaws}")
    print("-" * 60)
    print(f"  PRECISION (Flag Accuracy):     {precision * 100:.1f}%")
    print(f"  RECALL (Coverage of Flaws):    {recall * 100:.1f}%")
    print(f"  PIPELINE HALLUCINATION RATE:   {hallucination_rate * 100:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluations()
