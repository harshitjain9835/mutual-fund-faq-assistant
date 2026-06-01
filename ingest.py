"""Source ingestion module for the Mutual Fund FAQ Assistant."""

from __future__ import annotations

import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw_sources"
INGESTED_FILE = DATA_DIR / "ingested_sources.json"

SOURCE_URLS = [
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
]

FACT_FIELDS = {
    "overview": [r"overview|about this fund|scheme overview|investment objective"],
    "expense_ratio": [r"expense.*ratio|total expenses|total expense ratio|expense ratio"],
    "exit_load": [r"exit load|exit charge|exit fee|redemption charge"],
    "minimum_investment": [r"minimum.*investment|minimum.*sip|minimum investment|minimum SIP|initial investment|lump sum"],
    "benchmark": [r"benchmark|index"],
    "tax": [r"tax|capital gains|tax benefit|taxation"],
    "fund_management": [r"fund manager|managed by|management tenure|portfolio manager|scheme manager"],
    "investment_objective": [r"investment objective|objective of the scheme"],
    "fund_house": [r"fund house|asset management company|AMC|HDFC Asset Management"],
}


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def fetch_url(url: str, timeout: int = 20) -> Dict[str, Optional[str]]:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "url": url,
            "status": "error",
            "error": str(exc),
            "content_type": None,
            "content": None,
        }

    content_type = response.headers.get("Content-Type", "").lower()
    return {
        "url": url,
        "status": "ok",
        "error": None,
        "content_type": content_type,
        "content": response.content,
    }


def is_pdf(url: str, content_type: str) -> bool:
    return "pdf" in content_type or url.lower().endswith(".pdf")


def extract_text_from_html(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return normalize_text(text)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts: List[str] = []
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    except Exception:
        return ""
    return normalize_text("\n".join(text_parts))


def normalize_text(raw_text: str) -> str:
    text = re.sub(r"\r\n?|\n", "\n", raw_text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def split_paragraphs(text: str) -> List[str]:
    return [para.strip() for para in text.split("\n\n") if para.strip()]


def extract_sentence_at(text: str, index: int) -> str:
    left = text.rfind(".", 0, index) + 1
    right = text.find(".", index)
    if right == -1:
        right = len(text)
    return text[left:right].strip()


def extract_fact(text: str, patterns: List[str]) -> str:
    normalized = text.lower()
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        match = regex.search(text)
        if match:
            snippet = extract_sentence_at(text, match.start())
            return normalize_text(snippet)

    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        paragraph = next((p for p in split_paragraphs(text) if regex.search(p)), None)
        if paragraph:
            return normalize_text(paragraph)

    return ""


def extract_overview(text: str) -> str:
    for pattern in FACT_FIELDS["overview"]:
        regex = re.compile(pattern, re.IGNORECASE)
        paragraph = next((p for p in split_paragraphs(text) if regex.search(p)), None)
        if paragraph:
            return normalize_text(paragraph)
    paragraphs = split_paragraphs(text)
    return paragraphs[0] if paragraphs else ""


def extract_facts(text: str) -> Dict[str, str]:
    facts: Dict[str, str] = {}
    facts["overview"] = extract_overview(text)
    for field, patterns in FACT_FIELDS.items():
        if field == "overview":
            continue
        facts[field] = extract_fact(text, patterns)
    return facts


def build_source_entry(url: str) -> Dict[str, object]:
    fetched = fetch_url(url)
    if fetched["status"] != "ok" or fetched["content"] is None:
        return {
            "url": url,
            "status": fetched["status"],
            "error": fetched.get("error"),
            "content_type": fetched.get("content_type"),
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
            "text": "",
            "facts": {},
        }

    content_type = fetched["content_type"] or ""
    raw_content = fetched["content"]
    if is_pdf(url, content_type):
        text = extract_text_from_pdf(raw_content)
    else:
        text = extract_text_from_html(raw_content)

    return {
        "url": url,
        "status": "ok",
        "error": None,
        "content_type": content_type,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "text": text,
        "facts": extract_facts(text),
    }


def save_ingested_sources(entries: List[Dict[str, object]]) -> None:
    ensure_directories()
    with INGESTED_FILE.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)


def ingest_sources(source_urls: List[str]) -> List[Dict[str, object]]:
    ensure_directories()
    entries: List[Dict[str, object]] = []
    for url in source_urls:
        entry = build_source_entry(url)
        entries.append(entry)
    save_ingested_sources(entries)
    return entries


def load_ingested_sources() -> List[Dict[str, object]]:
    if not INGESTED_FILE.exists():
        return []
    with INGESTED_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    results = ingest_sources(SOURCE_URLS)
    summary = [f"{item['url']} -> {item['status']}" for item in results]
    print("Ingestion complete")
    print("\n".join(summary))
