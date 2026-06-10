"""
Embeddings & Semantic Search Service
- ChromaDB / FAISS vector store integration
- Duplicate detection via cosine similarity
- Natural language expense search with hybrid SQL fallback
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "expense_bills"


# ── Embedding Model Factory ───────────────────────────────────────────────────
def get_embeddings():
    if settings.LLM_PROVIDER == "groq":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
        )
    else:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=settings.OLLAMA_BASE_URL,
        )


# ── Vector Store Factory ──────────────────────────────────────────────────────
def get_vector_store():
    embeddings = get_embeddings()
    if settings.VECTOR_STORE == "chroma":
        from langchain_chroma import Chroma
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
    else:
        from langchain_community.vectorstores import FAISS
        import os
        faiss_path = "./faiss_index"
        if os.path.exists(f"{faiss_path}/index.faiss"):
            return FAISS.load_local(faiss_path, embeddings, allow_dangerous_deserialization=True)
        # Return empty FAISS store
        return FAISS.from_texts(["init"], embeddings, metadatas=[{"init": True}])


# ── Document Builder ──────────────────────────────────────────────────────────
def build_document_text(bill_id: str, metadata: dict) -> str:
    """Build a rich text representation for embedding."""
    parts = [
        f"Bill ID: {bill_id}",
        f"Vendor: {metadata.get('vendor_name', 'Unknown')}",
        f"Category: {metadata.get('category', 'Miscellaneous')}",
        f"Amount: {metadata.get('total_amount', 0)} {metadata.get('currency', 'INR')}",
        f"Date: {metadata.get('bill_date', '')}",
        f"Payment: {metadata.get('payment_method', '')}",
        f"Notes: {metadata.get('notes', '')}",
        f"OCR: {metadata.get('ocr_text', '')[:500]}",  # truncated OCR for context
    ]
    return " | ".join(filter(None, parts))


# ── Embeddings Service ────────────────────────────────────────────────────────
class EmbeddingsService:
    """
    Manages the lifecycle of bill embeddings:
    - Indexing new bills
    - Duplicate detection
    - Natural language semantic search
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.embeddings = get_embeddings()

    async def index_bill(
        self,
        bill_id: str,
        expense_metadata: dict,
        ocr_text: str,
    ) -> str:
        """
        Index a bill in the vector store.
        Returns the chroma doc ID.
        """
        meta = {**expense_metadata, "ocr_text": ocr_text, "bill_id": bill_id}
        doc_text = build_document_text(bill_id, meta)
        doc_id = str(uuid.uuid4())

        # Filter metadata — ChromaDB only accepts str/int/float/bool
        safe_meta = {
            k: str(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in meta.items()
            if v is not None
        }

        self.vector_store.add_texts(
            texts=[doc_text],
            metadatas=[safe_meta],
            ids=[doc_id],
        )
        logger.info(f"Indexed bill {bill_id} with doc_id {doc_id}")
        return doc_id

    async def find_duplicates(
        self,
        bill_id: str,
        expense_metadata: dict,
        ocr_text: str,
        threshold: float = 0.88,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar bills.
        Returns list of potential duplicates above the threshold.
        """
        doc_text = build_document_text(bill_id, {**expense_metadata, "ocr_text": ocr_text})

        results = self.vector_store.similarity_search_with_score(
            query=doc_text,
            k=5,
        )

        duplicates = []
        for doc, score in results:
            meta = doc.metadata
            found_bill_id = meta.get("bill_id")

            # Skip self
            if found_bill_id == bill_id:
                continue

            # ChromaDB returns distance (lower = more similar), normalize to similarity
            similarity = 1.0 - score if score <= 1.0 else 1.0 / (1.0 + score)

            if similarity >= threshold:
                confidence = (
                    "high" if similarity >= 0.95
                    else "medium" if similarity >= 0.90
                    else "low"
                )
                duplicates.append({
                    "bill_id": found_bill_id,
                    "similarity_score": round(similarity, 4),
                    "confidence": confidence,
                    "vendor": meta.get("vendor_name"),
                    "amount": meta.get("total_amount"),
                    "date": meta.get("bill_date"),
                })

        return sorted(duplicates, key=lambda x: x["similarity_score"], reverse=True)

    async def semantic_search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        Natural language search over indexed bills.
        Returns list of (bill_id, similarity_score, metadata).
        """
        where_clause = None
        if filters:
            # ChromaDB where clause for metadata filtering
            conditions = []
            if filters.get("category"):
                conditions.append({"category": {"$eq": filters["category"]}})
            if filters.get("min_amount"):
                conditions.append({"total_amount": {"$gte": str(filters["min_amount"])}})
            if conditions:
                where_clause = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        search_kwargs = {"k": k}
        if where_clause:
            search_kwargs["filter"] = where_clause

        results = self.vector_store.similarity_search_with_score(
            query=query,
            **search_kwargs,
        )

        output = []
        for doc, score in results:
            meta = doc.metadata
            bill_id = meta.get("bill_id")
            if not bill_id:
                continue
            similarity = 1.0 - score if score <= 1.0 else 1.0 / (1.0 + score)
            output.append((bill_id, round(similarity, 4), meta))

        return output

    async def delete_bill(self, chroma_doc_id: str) -> None:
        """Remove a bill's embedding from the vector store."""
        try:
            self.vector_store.delete(ids=[chroma_doc_id])
            logger.info(f"Deleted embedding {chroma_doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete embedding {chroma_doc_id}: {e}")


# Singleton
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
