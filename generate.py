"""Response generation module for the mutual fund assistant."""

import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

# Load environment variables from a .env file if present
load_dotenv()

# Initialize the OpenAI client pointing to the Groq API
api_key = os.environ.get("GROQ_API_KEY")

# Fallback to Streamlit secrets if not found in environment variables
if not api_key:
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass

client = Groq(
    api_key=api_key
) if api_key else None


def generate_answer(query: str, passages: List[Dict[str, Any]]) -> str:
    """Generate a concise, cited answer from grounding context."""
    # Handle refusal or unavailable errors from the retrieval module
    if not passages or "error" in passages[0]:
        return passages[0].get("message", "Information not found.")
        
    best_passage = passages[0]
    text = best_passage.get("text", "")
    url = best_passage.get("metadata", {}).get("url", "#")
    fetched_at = best_passage.get("metadata", {}).get("fetched_at", "Unknown date")[:10]
    
    if not client:
        return f"**[Error: GROQ_API_KEY not set. Placeholder Answer]**\n\n{text}\n\n**Source:** {url}\n\n*Last updated from sources: {fetched_at}*"

    system_prompt = (
        "You are a strict, facts-only mutual fund assistant. "
        "Answer the user's query using ONLY the provided context. "
        "Limit your answer to a maximum of 3 sentences. "
        "Do not provide investment advice. "
        "If the answer cannot be found in the context, state that the information is unavailable."
    )

    user_prompt = f"Context:\n{text}\n\nQuery: {query}"

    try:
        llm_response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=150
        )
        llm_answer = llm_response.choices[0].message.content.strip()
    except Exception as e:
        llm_answer = f"*[LLM Generation Error: {str(e)}]*"

    response = f"{llm_answer}\n\n**Source:** {url}\n\n*Last updated from sources: {fetched_at}*"
    
    return response

if __name__ == "__main__":
    print("Running LLM Generation Tests (Live API Calls)...\n")

    # Test 1: Standard Factual Query
    test_query_1 = "What is the expense ratio?"
    test_passages_1 = [
        {
            "text": "The total expense ratio of the HDFC Mid Cap fund is 1.05% p.a. as per the latest regulatory filings.",
            "metadata": {
                "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                "fetched_at": "2024-05-20T10:00:00Z"
            }
        }
    ]

    print(f"Test 1 - Query: {test_query_1}")
    print("-" * 40)
    print(generate_answer(test_query_1, test_passages_1))
    print("\n" + "=" * 60 + "\n")

    # Test 2: Unavailable Data Fallback
    test_query_2 = "Who is the fund manager?"
    test_passages_2 = [
        {"error": "unavailable", "message": "Information not found in the official sources."}
    ]
    print(f"Test 2 - Query: {test_query_2} (Simulated Unavailable)")
    print("-" * 40)
    print(generate_answer(test_query_2, test_passages_2))
    print("\n" + "=" * 60 + "\n")

    # Test 3: Refusal / Advisory Query Fallback
    test_query_3 = "Should I invest in this fund?"
    test_passages_3 = [
        {"error": "refusal", "message": "Advisory/non-factual query detected. The assistant only answers factual queries."}
    ]
    print(f"Test 3 - Query: {test_query_3} (Simulated Refusal)")
    print("-" * 40)
    print(generate_answer(test_query_3, test_passages_3))
