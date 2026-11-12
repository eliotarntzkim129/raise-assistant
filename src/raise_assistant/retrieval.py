from __future__ import annotations

import re
from typing import Any

from .db import Database


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "we", "what", "when", "where", "which", "with",
}

# Only these document classes may support customer-specific factual claims.
# Templates, assessor feedback, and failed submissions have separate roles and
# must never leak into ordinary retrieval as if they were customer evidence.
GROUNDING_KINDS = ("customer", "brief", "reference", "discovery_approved")


def fts_query(text: str) -> str:
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_.-]{1,}", text)]
    useful = []
    for token in tokens:
        clean = token.replace('"', "")
        if clean not in STOPWORDS and clean not in useful:
            useful.append(clean)
    return " OR ".join(f'"{token}"' for token in useful[:24])


def retrieve(
    db: Database,
    project_id: str,
    query: str,
    limit: int = 12,
    kinds: tuple[str, ...] = GROUNDING_KINDS,
) -> list[dict[str, Any]]:
    expression = fts_query(query)
    if not expression:
        return db.recent_chunks(project_id, limit, kinds)
    try:
        results = db.search_chunks(project_id, expression, limit, kinds)
    except Exception:
        results = []
    return results or db.recent_chunks(project_id, min(limit, 6), kinds)


def format_context(chunks: list[dict[str, Any]], max_chars: int = 42000) -> tuple[str, list[dict[str, Any]]]:
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    size = 0
    for index, chunk in enumerate(chunks, start=1):
        tag = f"S{index}"
        block = f"[{tag}] {chunk['source']} — {chunk['locator']}\n{chunk['text'].strip()}"
        if blocks and size + len(block) > max_chars:
            break
        blocks.append(block)
        size += len(block)
        sources.append(
            {
                "id": tag,
                "document_id": chunk["document_id"],
                "source": chunk["source"],
                "locator": chunk["locator"],
            }
        )
    return "\n\n".join(blocks), sources

