import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy import delete
from app.models.expense import Expense


async def _create_export_expenses(async_session, test_user):
    expense_a = Expense(
        user_id=test_user.id,
        vendor_name="Acme Supplies",
        bill_number="INV-1001",
        total_amount=Decimal("150.00"),
        tax_amount=Decimal("15.00"),
        expense_date=date(2026, 6, 15),
        currency="INR",
        category_name="Travel",
    )
    expense_b = Expense(
        user_id=test_user.id,
        vendor_name="Other Vendor",
        bill_number="INV-1002",
        total_amount=Decimal("60.00"),
        tax_amount=Decimal("6.00"),
        expense_date=date(2026, 6, 20),
        currency="INR",
        category_name="Food",
    )
    async_session.add_all([expense_a, expense_b])
    await async_session.commit()
    return [expense_a, expense_b]


async def _reset_expenses(async_session):
    await async_session.execute(delete(Expense))
    await async_session.commit()


@pytest.mark.asyncio
async def test_export_csv_vendor_filter(client, async_session, test_user):
    await _reset_expenses(async_session)
    await _create_export_expenses(async_session, test_user)

    response = await client.get(
        "/api/v1/reports/export",
        params={
            "format": "csv",
            "vendor": "Acme",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="expenses.csv"'
    assert b"Acme Supplies" in response.content
    assert b"Other Vendor" not in response.content


@pytest.mark.asyncio
async def test_export_xlsx_vendor_filter(client, async_session, test_user):
    await _reset_expenses(async_session)
    await _create_export_expenses(async_session, test_user)

    response = await client.get(
        "/api/v1/reports/export",
        params={
            "format": "xlsx",
            "vendor": "Acme",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_export_pdf_vendor_filter(client, async_session, test_user):
    await _reset_expenses(async_session)
    await _create_export_expenses(async_session, test_user)

    response = await client.get(
        "/api/v1/reports/export",
        params={
            "format": "pdf",
            "vendor": "Acme",
            "date_from": "2026-06-01",
            "date_to": "2026-06-30",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
