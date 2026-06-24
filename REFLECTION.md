# Design Decisions & Reflections

## 1. The Prompt Overfitting Challenge (V1 vs. V2)
During the initial implementation of the **Core (Tier 1)** pipeline, the Extractor Agent exhibited a classic LLM failure mode: **example overfitting**. 

- **The Issue**: By including specific text from *Privette v. Superior Court* (specifically page 695) in the formatting example, the model treated it as a strict structural mapping rather than a schema template. This caused the model to skip extracting the direct quote from page 702 ("A hirer is never liable...") and incorrectly merge different page pinpoints.
- **The Solution**: 
  - Abstracted the schema example with generic placeholders (e.g., `claim_1`, `Case Name v. Adversary`).
  - Instructed the LLM to scan the text chronologically and output separate entries for separate page pinpoints (even for the same case).
  - Configured `quote` to explicitly accept `null` so the model did not feel forced to fabricate a quote to satisfy the schema.

---

## 2. LLM vs. Rule-Based Regex for Extraction
A major architectural decision was whether to use deterministic regular expressions (Regex) or an LLM for the citation extraction phase.

### Deterministic Regex Approach
- **Pros**: Low latency, 100% deterministic, zero API cost.
- **Cons**: Extremely brittle for semantic binding. While regex can easily match `\d+\s+Cal\.\d+th\s+\d+`, it cannot associate the citation with the specific sentence it supports, resolve superscript footnotes to their text at the bottom of the page, or capture multi-clause sentences where different clauses belong to different citations.

### Pure LLM Approach (Selected)
- **Pros**: High semantic intelligence. The LLM understands syntax boundaries and correctly binds citations to the assertions they support, handles footnotes seamlessly, and extracts direct quotes regardless of formatting.
- **Cons**: Minor latency and API cost.
- **Verdict**: For a prototype, the pure LLM approach is superior because it fulfills the core requirement of structured, associated extraction. For a production MVP, a **hybrid approach** (using Regex to pre-detect text spans containing citations, and then using the LLM to perform semantic mapping) would optimize performance and reduce token costs.

---

## 3. Strict Verification Isolation
To prevent the Legal Authority Verifier from introducing external hallucinations, we established a strict **no web search** boundary. Instead, the agent relies entirely on the LLM's pre-trained knowledge base of landmark case law (e.g., California's *Privette* and *Seabright* doctrines). This successfully:
- Speed up the verification step.
- Correctly flagged fabricated cases (*Kellerman*, *Whitmore*) and footnote 1 cases.
- Avoided false positives that occur when search engines find case name collisions.
