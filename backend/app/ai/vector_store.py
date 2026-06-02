"""ChromaDB embedding store for semantic search and duplicate detection."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "bill_expenses"
_model: SentenceTransformer | None = None
_client: chromadb.ClientAPI | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_text(text: str) -> list[float]:
    return _get_model().encode(text, normalize_embeddings=True).tolist()


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


def upsert_bill_embedding(
    bill_id: int,
    user_id: int,
    document: str,
    metadata: dict[str, Any],
) -> str:
    chroma_id = f"bill_{bill_id}_{uuid.uuid4().hex[:8]}"
    embedding = embed_text(document)
    col = _collection()
    col.upsert(
        ids=[chroma_id],
        embeddings=[embedding],
        documents=[document],
        metadatas=[
            {
                **{k: (str(v) if v is not None else "") for k, v in metadata.items()},
                "bill_id": str(bill_id),
                "user_id": str(user_id),
            }
        ],
    )
    return chroma_id


def search_similar(
    query: str,
    user_id: int,
    n_results: int = 10,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    embedding = embed_text(query)
    filter_meta: dict[str, Any] = {"user_id": str(user_id)}
    if where:
        filter_meta.update({k: str(v) for k, v in where.items()})
    col = _collection()
    results = col.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=filter_meta,
        include=["documents", "metadatas", "distances"],
    )
    items: list[dict[str, Any]] = []
    if not results["ids"] or not results["ids"][0]:
        return items
    for i, cid in enumerate(results["ids"][0]):
        dist = results["distances"][0][i] if results["distances"] else 1.0
        similarity = 1.0 - dist
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        items.append(
            {
                "chroma_id": cid,
                "similarity_score": round(similarity, 4),
                "metadata": meta,
                "document": results["documents"][0][i] if results["documents"] else "",
            }
        )
    return items


def find_duplicates(
    document: str,
    user_id: int,
    bill_id: int,
    n_results: int = 5,
) -> list[dict[str, Any]]:
    matches = search_similar(document, user_id, n_results=n_results + 1)
    return [
        m
        for m in matches
        if str(m["metadata"].get("bill_id")) != str(bill_id)
        and m["similarity_score"] >= settings.DUPLICATE_SIMILARITY_THRESHOLD - 0.1
    ][:n_results]
