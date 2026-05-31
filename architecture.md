# Architecture Overview for the Mutual Fund FAQ Assistant

## Purpose
This architecture document describes the design of a facts-only mutual fund FAQ assistant built with a Retrieval-Augmented Generation (RAG) approach. The assistant is intended to answer objective, verifiable questions about mutual fund schemes using official sources only and to refuse any advisory or opinion-based requests.

## High-Level Architecture

The solution is composed of four main layers:

1. Corpus Collection and Ingestion
2. Retrieval and Embeddings
3. Response Generation and Safety
4. User Interface and Interaction

Each layer is designed to enforce the project constraints: short factual answers, single citations, official sources, and privacy compliance.

## Technology Stack

- **Corpus Ingestion**: `requests`, `BeautifulSoup4` (HTML parsing), and `PyPDF2` (PDF text extraction).
- **Embeddings & Vector Store**: OpenAI Embeddings (`text-embedding-3-small`) with an in-memory `numpy` vector index (using cosine similarity) for lightweight, local similarity search.
- **Language Model**: OpenAI API (`gpt-4o-mini` or similar) for intent classification and response generation based strictly on retrieved facts.
- **Frontend / UI**: Terminal-based CLI built with Python's standard `argparse` and interactive I/O for the initial Minimum Viable Product (MVP).

## 1. Corpus Collection and Ingestion

### Source Selection
- Official sources only: AMC websites, AMFI, SEBI.
- Example scheme pages currently limited to Groww URLs for selected HDFC funds:
  - https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth
  - https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth

### Document Types
- HTML scheme pages
- Factsheets and key information documents
- SID/KIM documents
- AMC FAQ/help pages
- AMFI/SEBI guidance pages
- Download guides for statements and tax reports

### Ingestion Process
- Fetch source documents via HTTP.
- Normalize content by extracting text from HTML and PDF.
- Store raw source metadata, including source URL and retrieval timestamp.
- Index extracted passages into an embedding-ready format.
- Track source freshness for the “Last updated from sources” footer.

## 2. Retrieval and Embeddings

### Vector Index
- Use sentence-level or passage-level embeddings to represent source text.
- Build a vector index to support similarity-based retrieval.
- Cache embeddings for efficiency and update when source documents change.

### Query Processing
- Normalize user queries: trim whitespace, remove punctuation, and preserve intent.
- Classify queries into factual vs. non-factual/advisory categories.
- Detect supported fact categories such as:
  - Expense ratio
  - Exit load details
  - Minimum SIP amount
  - ELSS lock-in period
  - Riskometer classification
  - Benchmark index
  - Fund management details (fund manager, tenure)
  - Process for downloading statements or capital gains reports

### Retrieval Strategy
- Retrieve top-K relevant passages from the vector index.
- Prefer passages that contain explicit factual statements over generic content.
- If the query is supported but answer is not found, return an explicit unavailable response rather than hallucinate.

## 3. Response Generation and Safety

### RAG Response Pipeline
- Use retrieved passages as grounding context for answer generation.
- Generate a concise response limited to a maximum of 3 sentences.
- Ensure each answer includes exactly one citation link from the source containing the supported fact.
- Append the footer:
  - “Last updated from sources: <date>”

### Citation and Source Handling
- Map the selected passage back to its origin URL.
- Include only one citation in the final response.
- If a single factual response relies on multiple sources, choose the most authoritative or sourceable citation and omit the rest.

### Advisory and Refusal Handling
- Refuse non-factual or advisory queries such as:
  - “Should I invest in this fund?”
  - “Which fund is better?”
- Refusal responses must be polite, clear, and compliant with the facts-only restriction.
- Provide an educational reference link to AMFI or SEBI for investor awareness.

### Privacy and Security Safeguards
- Do not collect or process PAN, Aadhaar, account numbers, OTPs, email addresses, or phone numbers.
- Reject or sanitize any user input containing sensitive identifiers.
- Maintain a facts-only response style without storing personal data.

## 4. User Interface and Interaction

### Minimal UI Requirements
- Display a welcome message.
- Show three example questions to guide users.
- Display a prominent disclaimer:
  - “Facts-only. No investment advice.”

### User Flow
1. User enters a question.
2. Query is classified and normalized.
3. Relevant source passages are retrieved from the corpus.
4. Response is generated with one citation and footer.
5. Answer is presented on the interface.

### Error and Fallback Behavior
- For empty or malformed queries, prompt the user to ask a factual mutual fund question.
- For unsupported questions, respond with a refusal message and educational link.
- For missing data, state that the information is unavailable from current sources.

## Design Considerations

### Strict Factuality
- Always ground answers in source text.
- Avoid inference beyond what the retrieved documents support.
- Use conservative generation to reduce hallucinations.

### Source Reliability
- Treat official AMC, AMFI, and SEBI URLs as the only valid citation domains.
- Exclude third-party blogs, aggregators, and opinion pages.

### Scalability and Maintainability
- Design ingestion as a modular pipeline to add new official sources.
- Keep retrieval and embedding components reusable for corpus expansion.
- Store source metadata and refresh timestamps to support ongoing updates.

## Architecture Diagram (Conceptual)

1. User UI
   - Input field
   - Example questions
   - Disclaimer

2. Query Processor
   - Normalization
   - Intent classification

3. Retrieval Engine
   - Embedding generation
   - Vector store
   - Passage ranking

4. Generation Engine
   - Answer construction
   - Citation selection
   - Footer injection

5. Source Store
   - Raw source documents
   - Metadata and freshness
   - URL-based citation mapping

## Known Limitations

- Current URL set is limited to Groww scheme pages, which may not cover all scheme facts or fund management details.
- Answers depend on the availability of official documents; unsupported or missing facts will be marked unavailable.
- Single-link citation may restrict how much context can be provided for complex queries.

## Conclusion

This architecture supports a lightweight, compliant RAG-based FAQ assistant that can answer mutual fund factual queries from official sources while enforcing strict facts-only behavior. The design prioritizes accuracy, transparency, and user safety through explicit citation, refusal handling, and source validation.