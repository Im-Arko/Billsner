from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import (
    ExpenseFilter,
    ExpenseResponse,
    ExpenseSearch,
    ExpenseSummary,
    ExpenseUpdate,
)
from app.services.expense_service import get_summary, list_expenses, semantic_search

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=list[ExpenseResponse])
async def list_user_expenses(
    filters: ExpenseFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, _ = await list_expenses(db, current_user.id, filters)
    return items


@router.post("/search", response_model=list[ExpenseResponse])
async def search_expenses(
    body: ExpenseSearch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await semantic_search(
        db, current_user.id, body.query, body.skip, body.limit
    )


@router.get("/summary", response_model=ExpenseSummary)
async def expense_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_summary(db, current_user.id)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    body: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id, Expense.user_id == current_user.id
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    await db.flush()
    return expense
