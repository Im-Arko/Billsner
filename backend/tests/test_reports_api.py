import asyncio
from datetime import date
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db, get_current_user
from app.database import Base
from app.main import app
from app.models.expense import Expense
from app.models.user import User


async def _prepare_test_database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        user = User(
            email="test@example.com",
            hashed_password="hashed-password",
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        expense_a = Expense(
            user_id=user.id,
            vendor_name="Acme Supplies",
            total_amount=Decimal("150.00"),
            tax_amount=Decimal("15.00"),
            expense_date=date(2026, 6, 15),
            currency="INR",
            category_name="Travel",
        )
        expense_b = Expense(
            user_id=user.id,
            vendor_name="Other Vendor",
            total_amount=Decimal("60.00"),
            tax_amount=Decimal("6.00"),
            expense_date=date(2026, 6, 20),
            currency="INR",
            category_name="Food",
        )
        session.add_all([expense_a, expense_b])
        await session.commit()

    async def _get_test_db():
        async with AsyncSessionLocal() as session:
            yield session

    return _get_test_db, user


def test_export_csv_vendor_filter():
    get_db_override, test_user = asyncio.run(_prepare_test_database())

    async def _override_current_user():
        return test_user

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = _override_current_user

    transport = ASGITransport(app=app)

    async def _send_request():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(
                "/api/v1/reports/export",
                params={
                    "format": "csv",
                    "vendor": "Acme",
                    "date_from": "2026-06-01",
                    "date_to": "2026-06-30",
                },
            )

    response = asyncio.run(_send_request())

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert "Acme Supplies" in response.text
    assert "Other Vendor" not in response.text
    assert response.headers["Content-Disposition"] == 'attachment; filename="expenses.csv"'
