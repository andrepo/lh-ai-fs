# Agents Definition & Architecture: BS Detector Prototype

This document defines the roles, responsibilities, input/output schemas, and boundaries of the four agents in the **BS Detector** verification pipeline.

---

## Agent Pipeline Overview

To ensure clear separation of concerns, the pipeline follows a sequential, modular workflow. Agents pass structured JSON payloads, and each agent has a strictly bounded responsibility.

```
[Motion for Summary Judgment (MSJ)]
               │
               ▼
┌──────────────────────────────┐
│  1. Claim & Citation Extractor│
└──────────────┬───────────────┘
               │ JSON: Extracted Claims & Citations
               ▼
      ┌────────┴────────┐
      ▼                 ▼
┌───────────┐     ┌───────────┐
│ 2. Factual│     │  3. Legal │
│ Verifier  │     │ Verifier  │
└─────┬─────┘     └─────┬─────┘
      │ JSON: Factual   │ JSON: Legal
      │ findings        │ findings
      └────────┬────────┘
               ▼
┌──────────────────────────────┐
│  4. Synthesizer & Scorer     │
└──────────────┬───────────────┘
               │
               ▼
     [Final Structured Report]
```

---

## 1. Claim & Citation Extractor (`extractor_agent`)

### Description
The Extractor Agent acts as the entry point of the pipeline. It parses the raw text of the Motion for Summary Judgment (MSJ) to identify and catalog every claim or reference that requires verification.

- **Role**: Document Parser and Feature Extractor
- **Inputs**: 
  - `msj_text` (string): The full text of the Motion for Summary Judgment.
- **Outputs**: 
  - `extracted_items` (JSON list): A list of items to verify, where each item has:
    - `id` (string): Unique identifier.
    - `category` (string): `"factual_assertion"` or `"legal_citation"`.
    - `statement` (string): The assertion or claim as stated in the MSJ.
    - `context` (string): The surrounding sentence or paragraph for context.
    - `citation_target` (string, optional): For citations, the specific case name/citation (e.g. *"Privette v. Superior Court, 5 Cal.4th 689"*).
- **Boundaries**: 
  - **Must Not**: Attempt to verify the truth of any claims.
  - **Must Not**: Read the police reports, medical records, or lookup cases.
  - **Must Not**: Alter or paraphrase the claims beyond extracting them.

---

## 2. Factual Consistency Verifier (`factual_verifier_agent`)

### Description
The Factual Consistency Verifier checks all factual claims made in the MSJ against the primary source evidence provided in the case files.

- **Role**: Fact-Checker and Evidence Corroborator
- **Inputs**:
  - `factual_assertions` (JSON list): The subset of items from Agent 1 with `category: "factual_assertion"`.
  - `source_documents` (JSON object): The text contents of `police_report.txt`, `medical_records_excerpt.txt`, and `witness_statement.txt`.
- **Outputs**:
  - `verified_factual_items` (JSON list): A list of evaluated factual assertions, where each item has:
    - `id` (string): Matching the input ID.
    - `statement` (string): The original statement.
    - `status` (string): `"supported" | "contradicted" | "unverified"`.
    - `confidence` (float): Confidence in this assessment (0.0 to 1.0).
    - `evidence` (string): The specific quote or section from the source documents that supports or contradicts the claim.
    - `source_file` (string): The file name where the evidence was found (e.g., *"police_report.txt"*). If unverified, this is blank.
    - `explanation` (string): Detailed rationale explaining why the claim is supported, contradicted, or why it cannot be verified.
- **Boundaries**:
  - **Must Not**: Evaluate legal arguments, legal citations, or case law.
  - **Must Not**: Use external knowledge to verify worksite events; it must rely *exclusively* on the provided source documents.
  - **Must Not**: Assume facts not in the records (if not mentioned, the status must be `"unverified"`).

---

## 3. Legal Authority Verifier (`legal_verifier_agent`)

### Description
The Legal Authority Verifier validates the legal assertions, case citations, and direct legal quotes in the MSJ. It ensures that the cited authorities actually exist, and that the legal principles stated in the MSJ align with the actual holdings of those cases.

- **Role**: Legal Scholar and Case Citator
- **Inputs**:
  - `legal_citations` (JSON list): The subset of items from Agent 1 with `category: "legal_citation"`.
- **Outputs**:
  - `verified_legal_items` (JSON list): A list of evaluated legal citations, where each item has:
    - `id` (string): Matching the input ID.
    - `statement` (string): The legal claim as asserted in the MSJ.
    - `citation_target` (string): The cited case/statute.
    - `status` (string): `"supported" | "mischaracterized" | "fabricated" | "unverified"`.
    - `confidence` (float): Confidence in this assessment (0.0 to 1.0).
    - `actual_holding` (string): The actual rule of law or holding of the cited case.
    - `explanation` (string): Rationale explaining how the MSJ's statement compares to the actual case law.
- **Boundaries**:
  - **Must Not**: Look at the factual worksite documents (police report, witness statement, etc.).
  - **Must Not**: Use web search tools or external APIs to verify case law; it must rely strictly on the LLM's internal knowledge base of legal case law and citations to determine validity.
  - **Must Not**: Determine if the defendant is liable or not based on the facts; it only checks if the legal citations are valid and correctly represented.

---

## 4. Judicial Synthesizer & Scorer (`synthesizer_agent`)

### Description
The Synthesizer & Scorer acts as the supervisor that consolidates all findings, scores them, and generates an executive overview.

- **Role**: Chief Editor and Judicial Summarizer
- **Inputs**:
  - `verified_factual_items` (JSON list): Outputs from Agent 2.
  - `verified_legal_items` (JSON list): Outputs from Agent 3.
- **Outputs**:
  - `overall_confidence` (float): Calculated reliability score of the MSJ (0.0 to 1.0).
  - `summary` (string): **The Judicial Memo**. A precise, single-paragraph summary written for a judge highlighting the key factual contradictions and legal fabrications found in the brief.
  - `findings` (JSON list): A merged list of all verified claims, sorted by priority (e.g. `fabricated` and `contradicted` claims first), with severity ratings (`"high" | "medium" | "low"`).
- **Boundaries**:
  - **Must Not**: Perform any independent verification or extraction. It must build its output strictly from the inputs provided by Agents 2 and 3.
  - **Must Not**: Write a long narrative report; the "summary" must be exactly one professional paragraph, and the rest of the findings must be structured JSON.
