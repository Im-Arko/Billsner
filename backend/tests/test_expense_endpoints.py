import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy import delete
from app.models.expense import Expense


async def _reset_expenses(async_session):
    await async_session.execute(delete(Expense))
    await async_session.commit()


async def _create_expense_records(async_session, test_user):
    item_a = Expense(
        user_id=test_user.id,
        vendor_name="Pizza Hut",
        bill_number="BILL-101",
        total_amount=Decimal("120.00"),
        tax_amount=Decimal("12.00"),
        expense_date=date(2026, 5, 10),
        currency="INR",
        category_name="Food",
        notes="Lunch meeting",
    )
    item_b = Expense(
        user_id=test_user.id,
        vendor_name="Transit Co",
        bill_number="BILL-102",
        total_amount=Decimal("80.00"),
        tax_amount=Decimal("8.00"),
        expense_date=date(2026, 5, 20),
        currency="INR",
        category_name="Travel",
        notes="Taxi ride",
    )
    async_session.add_all([item_a, item_b])
    await async_session.commit()
    return [item_a, item_b]


@pytest.mark.asyncio
async def test_expense_summary_returns_totals(client, async_session, test_user):
    await _reset_expenses(async_session)
    await _create_expense_records(async_session, test_user)

    response = await client.get("/api/v1/expenses/summary")
    assert response.status_code == 200

    payload = response.json()
    assert payload["expense_count"] == 2
    assert payload["duplicate_count"] == 0
    assert payload["total_expenses"] in {"200.00", "200"}
    assert payload["by_category"]["Food"] in {"120.00", "120"}
    assert payload["by_category"]["Travel"] in {"80.00", "80"}
    assert isinstance(payload["monthly_trend"], list)
    assert len(payload["recent_bills"]) == 0 or isinstance(payload["recent_bills"], list)


@pytest.mark.asyncio
async def test_search_expenses_can_parse_natural_language(client, async_session, test_user):
    await _reset_expenses(async_session)
    await _create_expense_records(async_session, test_user)

    response = await client.post(
        "/api/v1/expenses/search",
        json={"query": "food expenses from May at Pizza Hut", "limit": 20},
    )
    assert response.status_code == 200

    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["vendor_name"] == "Pizza Hut"
    assert results[0]["category_name"] == "Food"
