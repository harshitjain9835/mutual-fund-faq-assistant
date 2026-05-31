# Edge Case and Corner Case Scenarios

This document collects edge-case and corner-case scenarios for the Mutual Fund FAQ Assistant, based on `architecture.md` and `implementation-plan.md`.

## 1. Corpus Collection and Ingestion Edge Cases

### 1.1 Source Availability and Fetching
- Source URL returns 404, 500, timeout, or other HTTP error.
- Source redirects to a non-official domain or blocked page.
- Source uses anti-scraping protections or dynamic loading that prevents extraction.
- Source metadata is missing or malformed (no last-updated date).
- The URL list contains duplicate sources or multiple URLs pointing to the same underlying document.

### 1.2 Domain Constraint Violations
- Source is a third-party aggregator, blog, or non-official page.
- Source appears to be official but is not under AMC, AMFI, or SEBI control.
- A Groww page links to a non-official document as the source.

### 1.3 Document Type and Parsing
- Content is HTML with noisy navigation, page headers, or unrelated UI text.
- Content is PDF with poor extraction quality.
- PDF text extraction returns empty pages, scanned images, or broken character encoding.
- Documents contain tables, footnotes, disclaimers, and embedded charts that confuse extraction.

### 1.4 Fact Extraction and Normalization
- Required fact categories are absent in the source.
- A source includes contradictory values for the same fact in different sections.
- Numeric formats vary: “1% p.a.” vs. “1.00%” vs. “0.01” vs. “1 percent”.
- Dates appear in different formats or are ambiguous (e.g. 03/04/2024).
- Values include ranges, qualifiers, or conditional statements.

### 1.5 Metadata and Freshness
- Source freshness is unavailable, making footer date estimation impossible.
- Source content is stale but still accessible.
- Retrieving the same source multiple times yields different content.

## 2. Retrieval and Query Processing Edge Cases

### 2.1 Query Ambiguity and Intent
- User query is ambiguous between supported factual and unsupported advisory intent.
- Query asks for comparison or ranking: “which fund is better?”
- Query asks for recommendation or suitability: “should I invest?”
- Query mixes multiple questions in one input.
- Query uses slang, abbreviations, or local terms that may not map to the corpus.

### 2.2 Unsupported or Non-Factual Queries
- Query asks for opinions, advice, or performance predictions.
- Query asks for investment decisions, strategy, or portfolio construction.
- Query requests personal financial guidance or sensitive data handling.

### 2.3 Retrieval Quality
- Top-K retrieved passages are unrelated or low-relevance due to noisy corpus.
- Factual answer exists but is buried below irrelevant passages.
- Multiple retrieved passages conflict on the same fact.
- Retrieved passage lacks a clear source mapping.
- Query mentions a fund not present in the current limited corpus.

### 2.4 Boundary Fact Categories
- Query asks for fund management details but the source only states the AMC name.
- Query asks for scheme-specific data that only exists in PDFs or SID documents.
- Query asks for statement download procedure, but the source is a generic help page.
- Query asks for performance-related content, which should be redirected to a factsheet link only.

## 3. Response Generation and Safety Edge Cases

### 3.1 Citation and Footer Rules
- Generated response does not include any citation.
- Generated response includes multiple citations.
- Generated response cites an incorrect or non-official URL.
- Generated response includes a footer with no valid date or wrong date.
- Source mapping fails due to missing passage-to-URL linkage.

### 3.2 Length and Sentence Constraints
- Generated response exceeds the 3-sentence maximum.
- Response uses overly verbose language or explanatory text.
- Refusal response is too long or includes advice.

### 3.3 Hallucination and Inference
- Model fabricates a fact not present in the retrieved source.
- Model infers an answer from general knowledge rather than the provided corpus.
- Model combines multiple source facts into one unsupported statement.

### 3.4 Refusal Handling
- Advisory query is incorrectly answered factually.
- Non-factual query is answered with guidance instead of a refusal.
- Refusal lacks an AMFI or SEBI educational link.
- Refusal is phrased as a recommendation rather than a policy statement.

### 3.5 Privacy and Sensitive Data
- User asks for PAN, Aadhaar, account number, OTP, email, or phone number.
- Model attempts to accept or transform sensitive information.
- The assistant accidentally echoes personal identifiers from user input.

## 4. User Interface and Interaction Edge Cases

### 4.1 Input Handling
- Empty or whitespace-only input.
- Input with special characters, emojis, or unsupported Unicode.
- Very long queries or multi-sentence requests.
- Multiple questions submitted at once.

### 4.2 Display and UX
- UI fails to show the disclaimer or sample questions.
- The answer is displayed without the citation or footer.
- Error messaging is vague or does not explain why the query is unsupported.

### 4.3 Fallback Behavior
- The system cannot retrieve any relevant passage.
- The system returns an unavailable-data response but does not cite a reason.
- The UI shows a backend error instead of a user-friendly fallback.

## 5. System and Implementation Edge Cases

### 5.1 Infrastructure and Service Reliability
- Embedding service or model API is unavailable.
- Vector index storage is corrupted or missing.
- Rate limits are hit on external APIs.
- Cache and persistence layers become inconsistent.

### 5.2 Phase-Specific Risks
- Phase 2 ingestion pipeline fails on PDFs or dynamic pages.
- Phase 3 retrieval returns weak results due to an insufficient corpus.
- Phase 4 generation produces outputs that violate citation or sentence rules.
- Phase 5 UI integration fails to preserve the facts-only disclaimer.

### 5.3 Validation and Testing
- Tests rely on dynamic external sources that change or move.
- The system passes engineering tests but fails real-world query coverage.
- Compliance tests do not catch silent hallucinations or incorrect citations.

### 5.4 Maintenance and Extensibility
- Adding new official sources creates duplicate or inconsistent facts.
- Source refresh logic does not update embeddings after corpus changes.
- New fact categories are introduced without updating query classification.

## 6. Recommended Mitigation Strategies

- Validate source domains strictly and reject non-official URLs.
- Use conservative extraction and mark missing facts as unavailable.
- Implement a strong query classifier with explicit refusal rules.
- Force response templates to include one citation and one footer.
- Keep refusal templates separate from answer templates.
- Log retrieval and generation errors for review.
- Maintain a small, high-quality corpus for early MVP testing.
- Add automated tests for citation count, sentence length, and unsupported queries.
- Use fallback messages that clearly state whether data is unavailable or advice was refused.

## 7. Known Limits and Assumptions

- Current corpus is limited to a small set of Groww pages, so query coverage is narrow.
- Official source freshness is dependent on available metadata.
- The assistant is not designed to provide investment advice, comparisons, or personal financial guidance.
- Performance-related topics must be handled by redirecting to the official factsheet link only.
