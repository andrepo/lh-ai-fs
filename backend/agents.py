import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# Create LangChain OpenAI Chat models
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

llm_json = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    model_kwargs={"response_format": {"type": "json_object"}},
    openai_api_key=os.getenv("OPENAI_API_KEY")
)


def extractor_agent(msj_text: str) -> list[dict]:
    """
    Extracts all case law citations, statute citations, and factual assertions
    from the provided Motion for Summary Judgment (MSJ).
    """
    system_prompt = (
        "You are an expert legal document parser. Your job is to extract both:\n"
        "1. Legal citations (case law, code sections, statutes) and any accompanying assertions or direct quotes.\n"
        "2. Key factual assertions (e.g., statements about dates, events, entities, injuries, PPE, inspections, etc.), "
        "specifically focusing on Section II (Statement of Undisputed Material Facts) and other factual claims throughout the text.\n\n"
        "Instructions:\n"
        "1. Scan the text chronologically. Extract every citation and key factual assertion.\n"
        "2. Categorize each item into 'category': 'legal_citation' or 'factual_assertion'.\n"
        "3. For 'legal_citation', extract the cited case/statute name into 'citation_target' and the sentence it supports into 'statement'. "
        "If a direct quote is present, extract it verbatim into 'quote'. If no direct quote is present, set 'quote' to null.\n"
        "4. For 'factual_assertion', extract the factual sentence/assertion as written in the MSJ into 'statement'. "
        "Set 'citation_target' to null and 'quote' to null.\n"
        "5. Footnote Citations: You must scan footnotes at the bottom of the text. For footnote lists containing multiple case citations "
        "(such as footnote 1 with Torres, Blackwell, Dixon, Okafor, Nguyen, Reeves), extract EACH case citation as a separate, distinct 'legal_citation' item. "
        "Map each footnote citation to the sentence in the main body that contains the superscript footnote reference number (e.g., the sentence ending in '...insulating it from tort liability predicated on alleged safety failures at the site.1').\n"
        "6. Critical: Do not combine different sentences or different page pinpoints into a single item. If a case is cited multiple times for different points, create distinct entries.\n\n"
        "Output Format:\n"
        "Return ONLY a JSON object with this exact structure (use placeholders as schema guide only):\n"
        "{\n"
        "  \"extracted_items\": [\n"
        "    {\n"
        "      \"id\": \"string (e.g., item_1, item_2)\",\n"
        "      \"category\": \"string (legal_citation | factual_assertion)\",\n"
        "      \"statement\": \"string (the literal claim or sentence in the MSJ)\",\n"
        "      \"citation_target\": \"string or null (the cited case/statute name if legal_citation; otherwise null)\",\n"
        "      \"quote\": \"string or null (the verbatim direct quote if legal_citation and present; otherwise null)\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Be extremely thorough and literal. Do not summarize or synthesize. Extract text exactly as it appears in the document."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Here is the Motion for Summary Judgment text:\n\n{msj_text}")
    ]

    try:
        response = llm_json.invoke(messages)
        data = json.loads(response.content)
        return data.get("extracted_items", [])
    except Exception as e:
        print(f"Error in extractor_agent: {e}")
        return []


def legal_verifier_agent(extracted_items: list[dict]) -> list[dict]:
    """
    Validates the existence, holdings, and quotes of the extracted legal citations
    using the LLM's internal legal knowledge (no web search allowed), including confidence ratings.
    """
    system_prompt = (
        "You are an expert legal researcher and case citation verifier. You are given a list of legal citations, "
        "propositions, and direct quotes extracted from a Motion for Summary Judgment (MSJ).\n\n"
        "Your task is to verify each item using your internal knowledge of California and Federal law. DO NOT use web search.\n\n"
        "For each item, perform four checks:\n"
        "1. **Existence**: Does the cited case or statute exist? Check if the volume, reporter, and page numbers are accurate. "
        "If the case is entirely fabricated (like 'Kellerman v. Pacific Coast Construction, Inc., 887 F.2d 1204' or 'Whitmore v. Delgado Scaffolding Co., 334 F. Supp. 2d 1189'), flag it as fabricated.\n"
        "2. **Support**: Does the case actually hold the principle asserted? Does it support the statement? "
        "If the case is real but the statement mischaracterizes the holding, flag it as mischaracterized.\n"
        "3. **Quote Accuracy**: If a 'quote' is provided, check if it matches the actual text in the case verbatim. "
        "Note any significant discrepancies, additions, or omissions.\n"
        "4. **Confidence**: Assess your certainty level for the existence and holding of this case/statute, rating it as a float from 0.0 to 1.0, with a short explanation.\n\n"
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
        "      \"explanation\": \"Privette is a landmark California Supreme Court case. The statement accurately reflects the presumptive rule, and the quote matches the text in the case.\",\n"
        "      \"confidence\": 1.0,\n"
        "      \"confidence_explanation\": \"Privette is an extremely well-established California precedent with clear citation details.\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Here is the JSON list of extracted items to verify:\n\n{json.dumps(extracted_items, indent=2)}")
    ]

    try:
        response = llm_json.invoke(messages)
        data = json.loads(response.content)
        return data.get("verified_items", [])
    except Exception as e:
        print(f"Error in legal_verifier_agent: {e}")
        return []


def factual_verifier_agent(factual_assertions: list[dict], source_docs: dict[str, str]) -> list[dict]:
    """
    Compares the factual assertions against the provided source documents (police report,
    medical records, witness statement) to check for consistency and contradictions, including confidence ratings.
    """
    system_prompt = (
        "You are an expert fact-checker. You are given a list of factual assertions from a Motion "
        "for Summary Judgment (MSJ), and the text of several primary source documents (police report, "
        "medical records, and witness statement).\n\n"
        "Your task is to verify whether each factual assertion is supported, contradicted, or unverified by the evidence.\n\n"
        "Instructions:\n"
        "1. For each assertion, search the source documents for relevant evidence.\n"
        "2. Assign a 'status':\n"
        "   - 'supported': There is explicit evidence in the source documents confirming the assertion.\n"
        "   - 'contradicted': The source documents contain evidence that directly contradicts the assertion (e.g. different dates, different PPE status).\n"
        "   - 'could_not_verify': The source documents do not contain any information to either confirm or refute the assertion. Express uncertainty appropriately, and do not assume or fabricate facts.\n"
        "3. Provide the 'evidence' (the verbatim quote from the source document that supports or contradicts the claim). If the status is 'could_not_verify', set this to null.\n"
        "4. Provide the 'source_file' (the name of the document file where the evidence was found, e.g., 'police_report.txt'). If 'could_not_verify', set this to null.\n"
        "5. Provide an 'explanation' detailing your rationale.\n"
        "6. Provide a 'confidence' score as a float from 0.0 to 1.0 based on how clear and definitive the evidence is in the source files, along with a 'confidence_explanation'.\n\n"
        "Output Format:\n"
        "Return ONLY a JSON object with this structure:\n"
        "{\n"
        "  \"verified_factual_items\": [\n"
        "    {\n"
        "      \"id\": \"item_1\",\n"
        "      \"statement\": \"Rivera was not wearing required personal protective equipment...\",\n"
        "      \"status\": \"contradicted\",\n"
        "      \"evidence\": \"Site supervisor Mark Ellison confirmed that Rivera was wearing a hard hat and harness consistent with site requirements at the time of the collapse.\",\n"
        "      \"source_file\": \"police_report.txt\",\n"
        "      \"explanation\": \"The claim that Rivera was not wearing PPE is directly contradicted by both the police report and witness statements, which confirm he was wearing his hard hat and safety harness.\",\n"
        "      \"confidence\": 1.0,\n"
        "      \"confidence_explanation\": \"The police report and supervisor statements explicitly confirm PPE presence, leaving no ambiguity.\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    user_content = {
        "factual_assertions": factual_assertions,
        "source_documents": source_docs
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(user_content, indent=2))
    ]

    try:
        response = llm_json.invoke(messages)
        data = json.loads(response.content)
        return data.get("verified_factual_items", [])
    except Exception as e:
        print(f"Error in factual_verifier_agent: {e}")
        return []


def synthesizer_agent(verified_factual: list[dict], verified_legal: list[dict]) -> dict:
    """
    Consolidates factual and legal verifications, assigns severity ratings,
    calculates an overall confidence score, and generates a one-paragraph
    Judicial Memo for a judge.
    """
    system_prompt = (
        "You are an expert Chief Editor and Judicial Summarizer. Your job is to analyze "
        "the verification reports of factual claims and legal citations from a Motion for "
        "Summary Judgment (MSJ) and synthesize them into a final executive report for a judge.\n\n"
        "Instructions:\n"
        "1. Write a precise, single-paragraph summary (called the 'Judicial Memo') written for a judge. "
        "Highlight the key factual contradictions (like wrong incident date or PPE status) and "
        "legal fabrications/mischaracterizations (like fabricated cases or altered quotes) found in the brief. "
        "Maintain a highly professional, objective, and authoritative judicial tone.\n"
        "2. Compute an 'overall_confidence' score as a float between 0.0 and 1.0 representing the reliability of the MSJ. "
        "A brief with fabricated cases or direct contradictions of primary worksite files should have a low score (e.g. 0.1 to 0.4). "
        "Explain your scoring rationale briefly in your thought process, but return only the raw float in the JSON field.\n"
        "3. Consolidate and prioritize all findings. Each finding in the merged 'findings' list must include:\n"
        "   - 'id': the original claim ID\n"
        "   - 'category': 'factual_assertion' or 'legal_citation'\n"
        "   - 'statement': the original statement/claim\n"
        "   - 'status': the verification status (e.g., supported, contradicted, could_not_verify, mischaracterized, fabricated)\n"
        "   - 'severity': 'high' | 'medium' | 'low'\n"
        "     - Assign 'high' for fabricated cases or contradicted facts.\n"
        "     - Assign 'medium' for mischaracterized cases/statutes.\n"
        "     - Assign 'low' for supported or unverified (could_not_verify) claims.\n"
        "   - 'explanation': the verifier's explanation\n"
        "   - 'confidence': the individual verifier's confidence score (float)\n"
        "   - 'confidence_explanation': the individual verifier's confidence explanation\n"
        "   - 'details': a nested JSON object containing specific fields (like 'evidence', 'source_file' for factual items; 'citation_target', 'quote_accuracy', 'actual_holding' for legal items)\n"
        "4. Sort the findings list so that 'high' severity items appear first, followed by 'medium', then 'low'.\n\n"
        "Output Format:\n"
        "Return ONLY a JSON object with this structure:\n"
        "{\n"
        "  \"overall_confidence\": 0.35,\n"
        "  \"summary\": \"The Judicial Memo paragraph...\",\n"
        "  \"findings\": [\n"
        "    {\n"
        "      \"id\": \"item_1\",\n"
        "      \"category\": \"factual_assertion\",\n"
        "      \"statement\": \"...\",\n"
        "      \"status\": \"contradicted\",\n"
        "      \"severity\": \"high\",\n"
        "      \"explanation\": \"...\",\n"
        "      \"confidence\": 1.0,\n"
        "      \"confidence_explanation\": \"...\",\n"
        "      \"details\": {\n"
        "        \"evidence\": \"...\",\n"
        "        \"source_file\": \"...\"\n"
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    user_content = {
        "verified_factual_items": verified_factual,
        "verified_legal_items": verified_legal
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(user_content, indent=2))
    ]

    try:
        response = llm_json.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        print(f"Error in synthesizer_agent: {e}")
        return {
            "overall_confidence": 0.0,
            "summary": f"Failed to synthesize results: {str(e)}",
            "findings": []
        }
