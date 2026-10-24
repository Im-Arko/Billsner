"""Persistent text similarity index. Uses SQLite and requires no model downloads.

The existing embedding function names are retained for pipeline compatibility.
Similarity is lexical cosine similarity, not neural semantic similarity.
"""

from collections import Counter
from contextlib import contextmanager
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from app.config import get_settings

settings = get_settings()
STOP_WORDS = {"vendor", "amount", "category", "date", "unknown", "the", "and", "of", "for", "in", "at", "from", "show", "expenses", "expense"}


@contextmanager
def _index():
    path = Path(settings.SEARCH_INDEX_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, bill_id INTEGER NOT NULL, user_id INTEGER NOT NULL, document TEXT NOT NULL, metadata TEXT NOT NULL)")
        connection.execute("CREATE INDEX IF NOT EXISTS documents_owner ON documents(user_id)")
        yield connection
        connection.commit()
    finally:
        connection.close()


def _features(text: str) -> Counter:
    tokens = [token for token in re.findall(r"[\w]+", text.casefold()) if token not in STOP_WORDS]
    return Counter(tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])])


def _similarity(left: Counter, right: Counter) -> float:
    numerator = sum(value * right.get(key, 0) for key, value in left.items())
    norm = math.sqrt(sum(v*v for v in left.values()) * sum(v*v for v in right.values()))
    return numerator / norm if norm else 0.0


def build_document_text(
    ocr_text: str,
    vendor: str | None,
    amount: float | None,
    category: str | None,
    expense_date: str | None,
) -> str:
    parts = [
        f"Vendor: {vendor or 'unknown'}",
        f"Amount: {amount}" if amount is not None else "",
        f"Category: {category or ''}",
        f"Date: {expense_date or ''}",
        ocr_text[:3000],
    ]
    return "\n".join(p for p in parts if p)



def upsert_bill_embedding(bill_id: int, user_id: int, document: str, metadata: dict[str, Any]) -> str:
    document_id = f"bill_{bill_id}"
    metadata = {**{k: str(v) if v is not None else "" for k, v in metadata.items()},
                "bill_id": str(bill_id), "user_id": str(user_id)}
    with _index() as connection:
        connection.execute(
            "INSERT INTO documents(id, bill_id, user_id, document, metadata) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, document=excluded.document, metadata=excluded.metadata",
            (document_id, bill_id, user_id, document, json.dumps(metadata)),
        )
    return document_id


def delete_bill_embeddings(bill_id: int, user_id: int) -> None:
    with _index() as connection:
        connection.execute("DELETE FROM documents WHERE bill_id=? AND user_id=?", (bill_id, user_id))


def search_similar(query: str, user_id: int, n_results: int = 10,
                   where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with _index() as connection:
        rows = connection.execute("SELECT id, document, metadata FROM documents WHERE user_id=?", (user_id,)).fetchall()
    features = _features(query)
    hits = []
    for document_id, document, metadata_json in rows:
        metadata = json.loads(metadata_json)
        if where and any(str(metadata.get(k)) != str(v) for k, v in where.items()):
            continue
        similarity = _similarity(features, _features(document))
        if similarity > 0:
            hits.append({"chroma_id": document_id, "document": document, "metadata": metadata,
                         "similarity_score": round(similarity, 4)})
    return sorted(hits, key=lambda item: item["similarity_score"], reverse=True)[:n_results]


def find_duplicates(document: str, user_id: int, bill_id: int, n_results: int = 5) -> list[dict[str, Any]]:
    matches = search_similar(document, user_id, n_results=n_results + 1)
    return [m for m in matches
            if str(m["metadata"].get("bill_id")) != str(bill_id)
            and m["similarity_score"] >= settings.DUPLICATE_SIMILARITY_THRESHOLD - 0.1][:n_results]
