import json
from llm import call_llm

def extractor_agent(msj_text: str) -> list[dict]:
    """
    Extracts all case law citations, statute citations, and direct quotes
    from the provided Motion for Summary Judgment (MSJ).
    """
    system_prompt = (
        "You are an expert legal document parser. Your job is to extract all legal citations "
        "(case law, code sections, statutes) and any accompanying assertions or direct quotes "
        "from the provided Motion for Summary Judgment (MSJ).\n\n"
        "Instructions:\n"
        "1. Scan the text chronologically. Extract every single citation (including inside footnotes).\n"
        "2. For every citation, extract the surrounding sentence/proposition it is supporting into the 'statement' field.\n"
        "3. Check if the citation is immediately preceded or followed by a text enclosed in quotation marks (\"...\"). "
        "If a direct quote is present, extract it verbatim into the 'quote' field. If no direct quote exists for that specific citation, set 'quote' to null.\n"
        "4. Critical: Do not combine different sentences or different page pinpoints into a single item. If a case is cited multiple times for different points, create distinct entries.\n\n"
        "Output Format:\n"
        "Return ONLY a JSON object with this exact structure (use placeholders as schema guide only):\n"
        "{\n"
        "  \"extracted_items\": [\n"
        "    {\n"
        "      \"id\": \"string (e.g., claim_1, claim_2)\",\n"
        "      \"type\": \"string (legal_citation | statute_citation)\",\n"
        "      \"statement\": \"string (the literal assertion or sentence in the brief that relies on the citation)\",\n"
        "      \"citation_target\": \"string (the full case name, volume, reporter, page number, and year, exactly as written)\",\n"
        "      \"quote\": \"string or null (the verbatim direct quote wrapped in quotes if present; otherwise null)\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Be extremely thorough and literal. Do not summarize or synthesize. Extract text exactly as it appears in the document."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Here is the Motion for Summary Judgment text:\n\n{msj_text}"}
    ]

    response_text = call_llm(
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        data = json.loads(response_text)
        return data.get("extracted_items", [])
    except json.JSONDecodeError:
        return []


def legal_verifier_agent(extracted_items: list[dict]) -> list[dict]:
    """
    Validates the existence, holdings, and quotes of the extracted legal citations
    using the LLM's internal legal knowledge (no web search allowed).
    """
    system_prompt = (
        "You are an expert legal researcher and case citation verifier. You are given a list of legal citations, "
        "propositions, and direct quotes extracted from a Motion for Summary Judgment (MSJ).\n\n"
        "Your task is to verify each item using your internal knowledge of California and Federal law. DO NOT use web search.\n\n"
        "For each item, perform three checks:\n"
        "1. **Existence**: Does the cited case or statute exist? Check if the volume, reporter, and page numbers are accurate. "
        "If the case is entirely fabricated (like 'Kellerman v. Pacific Coast Construction, Inc., 887 F.2d 1204' or 'Whitmore v. Delgado Scaffolding Co., 334 F. Supp. 2d 1189'), flag it as fabricated.\n"
        "2. **Support**: Does the case actually hold the principle asserted? Does it support the statement? "
        "If the case is real but the statement mischaracterizes the holding, flag it as mischaracterized.\n"
        "3. **Quote Accuracy**: If a 'quote' is provided, check if it matches the actual text in the case verbatim. "
        "Note any significant discrepancies, additions, or omissions.\n\n"
        "Status definitions:\n"
        "- 'supported': The case exists and its holding supports the statement.\n"
        "- 'mischaracterized': The case exists, but the statement misrepresents or exaggerates its holding or scope.\n"
        "- 'fabricated': The case does not exist (the name, citation, or both are fabricated).\n"
        "- 'unverified': You do not have enough information to confirm the case's existence or holding.\n\n"
        "Quote accuracy definitions:\n"
        "- 'accurate': The quote is verbatim or contains only minor insignificant differences.\n"
        "- 'misquoted': The quote exists but has been modified, words removed or changed to alter meaning.\n"
        "- 'hallucinated': The quote does not exist in the cited case or the case itself is fabricated.\n"
        "- 'no_quote': No quote was provided for verification.\n\n"
        "Output Format:\n"
        "Return ONLY a JSON object with this structure:\n"
        "{\n"
        "  \"verified_items\": [\n"
        "    {\n"
        "      \"id\": \"claim_1\",\n"
        "      \"citation_target\": \"Privette v. Superior Court, 5 Cal.4th 689, 695 (1993)\",\n"
        "      \"statement\": \"...\",\n"
        "      \"status\": \"supported\",\n"
        "      \"quote_accuracy\": \"accurate\",\n"
        "      \"actual_holding\": \"Under the Privette doctrine, a hirer of an independent contractor is presumptively not liable for injuries to the contractor's employees...\",\n"
        "      \"explanation\": \"Privette is a landmark California Supreme Court case. The statement accurately reflects the presumptive rule, and the quote matches the text in the case.\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Here is the JSON list of extracted items to verify:\n\n{json.dumps(extracted_items, indent=2)}"}
    ]

    response_text = call_llm(
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"}
    )

    try:
        data = json.loads(response_text)
        return data.get("verified_items", [])
    except json.JSONDecodeError:
        return []
