# Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Project Overview

This repository contains a facts-only Retrieval-Augmented Generation (RAG) assistant for mutual fund scheme queries. The assistant is designed to answer objective, verifiable questions using official sources only and to refuse any advisory or opinion-based requests.

## Phase 1: Setup and Scaffolding

This phase establishes the project structure and initial metadata.

### Completed
- Repo folder scaffolding verified: `src/`, `data/`, `docs/`, `scripts/`, `tests/`
- Added core documentation files: `architecture.md`, `implementation-plan.md`, `problemStatement.md`, `edge-case.md`
- Created placeholder source modules in `src/`
- Added `.gitignore`
- Confirmed core requirements and defined technology stack (documented in `architecture.md`)

## Technology Stack

- **Corpus Ingestion**: Python, `requests`, `BeautifulSoup4`, `PyPDF2`
- **Embeddings & Vector Store**: BGE Embeddings (`BAAI/bge-small-en-v1.5`) with local `ChromaDB`
- **Language Model**: Groq API (`llama3-8b-8192`)
- **Frontend / UI**: Terminal CLI and web-based UI using `Gradio`

## Repository Structure

- `src/` - source code modules and service stubs
- `data/` - corpus storage and ingestion outputs
- `docs/` - supporting documentation and problem statements
- `scripts/` - helper scripts and project utilities
- `tests/` - test suite for validation

## Setup Instructions

1. Clone the repository.
2. Set up a Python virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set your Groq API key as an environment variable or in a `.env` file:
   ```bash
   export GROQ_API_KEY="your-groq-api-key-here"
   ```

## Usage

The application is controlled via the `src/app.py` entry point. From the repository root, you can run the following commands:

**1. Ingest Data**
```bash
python src/app.py ingest
```

This will fetch the configured source URLs and save extracted content with metadata to `data/ingested_sources.json`.

## References

- `architecture.md`
- `implementation-plan.md`
- `problemStatement.md`
- `edge-case.md`
