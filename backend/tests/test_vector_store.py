import pytest

from app.ai import vector_store


@pytest.fixture
def index(tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store.settings, "SEARCH_INDEX_PATH", str(tmp_path / "search.db"))


def test_reprocessing_uses_one_stable_index_entry(index):
    first = vector_store.upsert_bill_embedding(42, 7, "Coffee receipt 100.00", {"expense_id": 9})
    second = vector_store.upsert_bill_embedding(42, 7, "Coffee receipt 100.00", {"expense_id": 9})
    assert first == second == "bill_42"
    hits = vector_store.search_similar("Coffee receipt 100.00", 7)
    assert len(hits) == 1
    assert hits[0]["similarity_score"] == 1.0


def test_index_cleanup_is_scoped_to_owner(index):
    vector_store.upsert_bill_embedding(42, 7, "Coffee receipt", {})
    vector_store.delete_bill_embeddings(42, 8)
    assert len(vector_store.search_similar("Coffee receipt", 7)) == 1
    vector_store.delete_bill_embeddings(42, 7)
    assert vector_store.search_similar("Coffee receipt", 7) == []


def test_search_cannot_override_owner(index):
    vector_store.upsert_bill_embedding(42, 7, "Coffee receipt", {})
    assert vector_store.search_similar("Coffee receipt", 8) == []
    assert vector_store.search_similar("Coffee receipt", 8, where={"user_id": "7"}) == []


def test_duplicates_exclude_self_and_other_users(index):
    vector_store.upsert_bill_embedding(42, 7, "Coffee receipt 100.00", {"expense_id": 9})
    vector_store.upsert_bill_embedding(43, 7, "Coffee receipt 100.00", {"expense_id": 10})
    vector_store.upsert_bill_embedding(44, 8, "Coffee receipt 100.00", {"expense_id": 11})
    hits = vector_store.find_duplicates("Coffee receipt 100.00", 7, 42)
    assert [hit["metadata"]["bill_id"] for hit in hits] == ["43"]
