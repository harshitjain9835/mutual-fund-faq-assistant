"""Retrieval module for selecting relevant factual passages."""

import json
import re
import sys
from typing import Any, Dict, List
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

# Load the BAAI BGE-Small model (Phase 3 Requirement)
MODEL_NAME = "BAAI/bge-small-en-v1.5"
embedder = SentenceTransformer(MODEL_NAME)

# Initialize a persistent local ChromaDB client
client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

# Use get_or_create to connect to the existing index or create a new one
collection = client.get_or_create_collection(name="mutual_fund_facts")

def get_corpus_file() -> Path:
    """Dynamically determine which corpus file is available."""
    corpus_json = DATA_DIR / "corpus.json"
    if corpus_json.exists():
        return corpus_json
    return DATA_DIR / "ingested_sources.json"

def normalize_query(query: str) -> str:
    """Trim whitespace, normalize casing, remove irrelevant punctuation."""
    q = query.strip().lower()
    q = re.sub(r'\s+', ' ', q)
    q = re.sub(r'[^\w\s\.\?\-]', '', q)
    return q

def is_factual_query(query: str) -> bool:
    """
    Detect factual requests vs. advisory/non-factual queries.
    Returns False if an advisory or comparison intent is detected.
    """
    advisory_patterns = [
        r"should i", r"recommend", r"best fund", r"better", r"compare",
        r"which one", r"good investment", r"invest in", r"buy or sell",
        r"my portfolio", r"forecast", r"prediction"
    ]
    for pattern in advisory_patterns:
        if re.search(pattern, query):
            return False
    return True

def chunk_text(text: str, words_per_chunk: int = 250, overlap: int = 50) -> List[str]:
    """Split raw text into overlapping chunks to fit model context windows."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max(1, words_per_chunk - overlap)):
        chunk = " ".join(words[i:i + words_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

def build_index() -> None:
    """Read the corpus, generate BGE embeddings, and load into ChromaDB."""
    corpus_file = get_corpus_file()
    if not corpus_file.exists():
        print(f"Error: Corpus file not found at {corpus_file}")
        return
        
    with open(corpus_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if isinstance(data, list):
        sources = data
    else:
        sources = data.get("sources", data.get("documents", data.get("data", [])))
    docs, metadatas, ids = [], [], []
    
    chunk_id = 0
    for source in sources:
        url = source.get("url", "")
        fetched_at = source.get("fetched_at") or source.get("retrieved_at", "")
        
        # Index the structured 'facts' to enforce highly accurate top-K results
        facts = source.get("facts", {})
        for fact_key, fact_value in facts.items():
            if fact_value and isinstance(fact_value, str):
                docs.append(f"{fact_key.replace('_', ' ').title()}: {fact_value}")
                metadatas.append({"url": url, "fetched_at": fetched_at, "type": "fact"})
                ids.append(f"fact_{chunk_id}")
                chunk_id += 1
                
        # Index the general text chunks
        raw_passages = source.get("passages")
        # Fallback to chunking raw text if running from ingested_sources.json
        if not raw_passages and "text" in source:
            raw_passages = [source.get("text", "")]
            
        final_passages = []
        for p in (raw_passages or []):
            if len(p.split()) > 300:
                final_passages.extend(chunk_text(p))
            else:
                final_passages.append(p)
                
        for p in final_passages:
            text = p.strip()
            if text:
                docs.append(text)
                metadatas.append({"url": url, "fetched_at": fetched_at, "type": "passage"})
                ids.append(f"passage_{chunk_id}")
                chunk_id += 1
                
    if not docs:
        print("No documents found in corpus to index.")
        return
        
    print(f"Generating embeddings for {len(docs)} chunks using {MODEL_NAME}...")
    embeddings = embedder.encode(docs, normalize_embeddings=True).tolist()
    
    print("Storing vectors in ChromaDB...")
    batch_size = 150
    for i in range(0, len(docs), batch_size):
        collection.upsert(
            documents=docs[i:i+batch_size],
            embeddings=embeddings[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )
    print(f"Successfully indexed {len(docs)} items into ChromaDB.")

def retrieve_passages(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve candidate passages for a given query."""
    
    if collection.count() == 0:
        print("Vector database is empty. Attempting to build index automatically...")
        build_index()
        if collection.count() == 0:
            return [{"error": "unavailable", "message": "The vector database is empty and could not be indexed automatically. Please ensure you have ingested the data first."}]

    norm_query = normalize_query(query)
    
    # Refuse advisory/non-factual questions before querying the database
    if not is_factual_query(norm_query):
        return [{"error": "refusal", "message": "Advisory/non-factual query detected. The assistant only answers factual queries."}]

    # BGE models require an instruction prefix for querying to maximize retrieval accuracy
    instruction = "Represent this sentence for searching relevant passages: "
    full_query = instruction + norm_query
    
    # normalize_embeddings=True allows Chroma to use optimal Cosine distance comparisons
    query_embedding = embedder.encode(full_query, normalize_embeddings=True).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    passages = []
    if results.get("documents") and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            dist = results["distances"][0][i] if results.get("distances") else None
            
            passages.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": dist
            })
            
    # Return an explicit unavailable result if no strong passage is found
    if not passages:
        return [{"error": "unavailable", "message": "Information not found in the official sources."}]
        
    return passages

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "index":
        build_index()
    elif len(sys.argv) > 2 and sys.argv[1] == "search":
        test_query = sys.argv[2]
        print(f"Searching for: '{test_query}'\n")
        res = retrieve_passages(test_query)
        print(json.dumps(res, indent=2))
    else:
        print("Usage:")
        print("  python src/retrieval.py index             (Build the vector database)")
        print("  python src/retrieval.py search \"<query>\"  (Test the retrieval logic)")
