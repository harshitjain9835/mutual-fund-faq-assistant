"""Response generation module for the mutual fund assistant."""

from typing import Any, Dict, List


def generate_answer(query: str, passages: List[Dict[str, Any]]) -> str:
    """Generate a concise, cited answer from grounding context."""
    # Handle refusal or unavailable errors from the retrieval module
    if not passages or "error" in passages[0]:
        return passages[0].get("message", "Information not found.")
        
    # Placeholder response until the Groq LLM API is integrated
    best_passage = passages[0]
    text = best_passage.get("text", "")
    url = best_passage.get("metadata", {}).get("url", "#")
    fetched_at = best_passage.get("metadata", {}).get("fetched_at", "Unknown date")[:10]
    
    response = f"**[Placeholder LLM Answer]**\n\n{text}\n\n**Source:** {url}\n\n*Last updated from sources: {fetched_at}*"
    
    return response
