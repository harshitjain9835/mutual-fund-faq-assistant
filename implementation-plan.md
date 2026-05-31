# Implementation Plan for the Mutual Fund FAQ Assistant

## Goal
Deliver a facts-only Retrieval-Augmented Generation (RAG) assistant for mutual fund scheme queries that responds with concise, verifiable answers and exactly one official source citation.

## Phase 1: Project Setup and Planning

### Objectives
- Establish repository structure
- Formalize project requirements from `problemStatement.md`
- Define architecture and tooling from `architecture.md`

### Tasks
1. Create project scaffold
   - Setup folders: `src/`, `data/`, `docs/`, `scripts/`
   - Add `README.md`
   - Add `.gitignore` and any necessary configuration files
2. Confirm core requirements
   - Facts-only query scope
   - Single citation and last-updated footer
   - Advisory refusal policy
   - Privacy safeguards
3. Define technology stack
   - Use BGE embeddings (`bge-small-en-v1.5`) via `sentence-transformers`
   - Use ChromaDB for local persistent vector storage and citation metadata handling
   - Use Groq API for high-speed LLM response generation
   - Choose frontend framework or UI approach
4. Draft detailed project milestones
   - Corpus ingestion
   - Retrieval index
   - Response generation
   - UI and validation

### Deliverables
- `README.md` with setup summary
- `architecture.md` and `problemStatement.md` aligned
- Project folder structure ready

## Phase 2: Corpus Collection and Ingestion

### Objectives
- Build a source ingestion pipeline for official mutual fund documents
- Normalize and store content for retrieval

### Tasks
1. Create source list
   - Start with current Groww URLs for selected HDFC funds
   - Identify additional official AMC, AMFI, and SEBI URLs if possible
2. Implement document fetcher
   - Fetch HTML pages and PDFs via HTTP
   - Handle redirects, 404s, timeouts, and HTTP errors
3. Extract and normalize text
   - Extract text from HTML content
   - Extract text from PDF documents if required
   - Clean up extracted passages: remove navigation text, preserve factual statements
   - Chunk normalized text into semantically coherent passages for retrieval
4. Store source metadata
   - Capture source URL, document type, retrieval timestamp, and last-updated date if available
   - Keep mapping from text passages to source URL for citation
5. Build ingestion validation checks
   - Verify source domain restrictions (AMC, AMFI, SEBI only)
   - Ensure extracted corpus includes key fact categories

### Chunking Strategy
- Use passage-level chunks, not whole documents.
- Chunk by section, heading, or paragraph boundaries where possible to preserve context.
- Target 250–320 words per chunk for better retrieval granularity while avoiding oversized vectors.
- Use 25–50 word overlaps between adjacent chunks to preserve continuity across split sections.
- Prefer grouping FAQ-friendly facts into the same chunk when they are topically related, especially for:
  - `expense_ratio`
  - `exit_load`
  - `minimum_investment`
  - `benchmark`
  - `tax`
  - `fund_management`
  - `investment_objective`
  - `fund_house`
- Avoid mixing unrelated scheme details in a single chunk; keep fund objective, management, and benchmark text separate from operational details where possible.
- Store chunk metadata with source URL, section heading (or inferred label), and retrieval timestamp so each chunk can be traced back to the source.
- Validate chunk length and drop extremely short or empty chunks to improve vector quality.

### Status
- Phase 2 is implemented and complete.
- `src/ingest.py` now supports source fetching, HTML/PDF extraction, normalization, fact extraction, and saving ingested corpus metadata.
- `data/ingested_sources.json` stores the ingested source corpus and metadata.

### Deliverables
- `data/` corpus store with source metadata
- Ingestion script in `src/ingest.py` or equivalent
- Logging for failed fetches and parsing issues

## Phase 3: Embeddings and Retrieval

### Objectives
- Build a retrieval engine that finds the best source passage for a user query

### Tasks
1. Create embedding workflow
   - Generate embeddings using `BAAI/bge-small-en-v1.5` for ingested document chunks
   - Prepend the required instruction prefix for user queries before embedding
2. Build vector index
   - Initialize a persistent local ChromaDB client to store vectors alongside source metadata (`url`, `fetched_at`)
   - Support top-K retrieval for relevant passages
3. Implement query normalization
   - Trim whitespace, normalize casing, remove irrelevant punctuation
   - Preserve meaning for factual query classification
4. Classify query intent
   - Detect factual requests vs. advisory/non-factual queries
   - Flag unsupported queries for refusal handling
5. Develop retrieval logic
   - Retrieve and rank relevant passages using vector similarity
   - Apply a distance threshold (e.g., 0.95 on normalized L2) to filter out generic or unrelated text
   - Return an explicit "unavailable" result if no strong passage meets the threshold

### Deliverables
- `src/retrieval.py` or equivalent
- Working vector index and retrieval test cases
- Intent classifier and query processing module

## Phase 4: Response Generation and Safety

### Objectives
- Generate concise, cited answers with strict compliance to facts-only and citation rules

### Tasks
1. Implement RAG generation pipeline
   - Integrate Groq LLM API for fast text generation
   - Use retrieved passage(s) as grounding context
   - Build a prompt template that requests 3 sentences max
   - Force exactly one citation link in output
2. Map responses to sources
   - Ensure citation matches the selected passage URL
   - Include footer “Last updated from sources: <date>” using source freshness data
3. Implement refusal logic
   - Create refusal templates for advisory questions
   - Include an AMFI or SEBI educational link in refusal responses
4. Enforce compliance rules
   - No investment advice
   - No performance comparisons or recommendations
   - No personal or sensitive data handling
5. Test output formatting
   - Validate sentence count
   - Validate single citation presence
   - Validate footer inclusion

### Deliverables
- `src/generate.py` or equivalent response engine
- Response validation tests
- Refusal response module

## Phase 5: Interface and User Interaction

### Objectives
- Build a simple user interface that displays welcome copy, example questions, and a disclaimer

### Tasks
1. Design minimal UI
   - Welcome message
   - Three example factual questions
   - Prominent disclaimer: “Facts-only. No investment advice.”
2. Implement frontend or CLI
   - Web-based UI using plain HTML/CSS/JS or lightweight framework
   - Alternatively, implement a terminal-based interface for initial MVP
3. Connect UI to backend
   - Send user query to retrieval and generation services
   - Display generated answer, citation, and footer
4. Add error handling
   - Handle empty queries
   - Display clear unsupported/refusal responses
   - Show unavailable-data messages when facts cannot be found

### Deliverables
- `src/app.py` or frontend equivalent
- UI with sample questions and disclaimer
- Basic input/output flow working end-to-end

## Phase 6: Testing and Validation

### Objectives
- Validate correctness, safety, and installation readiness

### Tasks
1. Functional tests
   - Test key factual queries: expense ratio, exit load, benchmark, fund manager, statement download process
   - Test refusal cases for advisory queries
2. Edge-case tests
   - Test missing source data
   - Test broken or unavailable URLs
   - Test query normalization and odd input formats
3. Compliance tests
   - Verify every response includes exactly one citation
   - Verify footer presence in all responses
   - Verify maximum of 3 sentences per answer
4. User acceptance tests
   - Confirm UI displays disclaimer and example questions
   - Confirm responses remain short and source-backed

### Deliverables
- Test suite in `tests/`
- Validation report for known limitations
- Updated documentation with any assumptions or constraints

## Phase 7: Documentation and Delivery

### Objectives
- Provide clear setup instructions, architecture summary, and usage guide

### Tasks
1. Complete `README.md`
   - Setup steps
   - Project scope
   - How to run the assistant
2. Document source list and selected AMC/schemes
   - List the initial Groww URLs and any official sources used
3. Capture limitations and future work
   - Notes about limited URL coverage
   - Notes about source freshness and missing fund management details
4. Deliver final artifacts
   - `README.md`
   - `architecture.md`
   - `implementation-plan.md`
   - `problemStatement.md`

### Deliverables
- Final README and docs
- Deployment or run instructions
- Summary of sources and constraints

## Phased Timeline Suggestion

- Week 1: Project setup, corpus ingestion prototype, architecture validation
- Week 2: Embeddings, retrieval engine, and query classification
- Week 3: Response generation, safety rules, and citation handling
- Week 4: Interface implementation, testing, and documentation

## Notes
- Keep the assistant aligned with the facts-only requirement throughout every phase.
- Prioritize source validity and refusal safety over broader coverage in early iterations.
- Use the architecture design as the reference for each implementation step.
