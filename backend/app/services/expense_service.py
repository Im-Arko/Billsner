"""Expense queries, analytics, and hybrid search."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import re

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.classifier import CATEGORIES, classify_by_keywords
from app.ai.vector_store import search_similar
from app.models.bill import Bill
from app.models.expense import Expense
from app.schemas.expense import ExpenseFilter, ExpenseSummary


def _apply_filters(stmt, user_id: int, filters: ExpenseFilter):
    conditions = [Expense.user_id == user_id]
    if filters.category:
        conditions.append(Expense.category_name.ilike(f"%{filters.category}%"))
    if filters.vendor:
        conditions.append(Expense.vendor_name.ilike(f"%{filters.vendor}%"))
    if filters.min_amount is not None:
        conditions.append(Expense.total_amount >= filters.min_amount)
    if filters.max_amount is not None:
        conditions.append(Expense.total_amount <= filters.max_amount)
    if filters.date_from:
        conditions.append(Expense.expense_date >= filters.date_from)
    if filters.date_to:
        conditions.append(Expense.expense_date <= filters.date_to)
    if filters.is_duplicate is not None:
        conditions.append(Expense.is_duplicate == filters.is_duplicate)
    return stmt.where(and_(*conditions))


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _extract_year(query: str) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", query)
    return int(match.group(0)) if match else None


def _parse_date_range(query: str) -> tuple[date | None, date | None]:
    normalized = query.lower()
    today = date.today()
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    if "last month" in normalized:
        year = today.year
        month = today.month - 1 or 12
        if month == 12:
            year -= 1
        return _month_range(year, month)

    if "this month" in normalized:
        return _month_range(today.year, today.month)

    for month_name, month_value in month_names.items():
        if re.search(rf"\b(?:in|from)\s+{month_name}\b", normalized):
            year = _extract_year(query) or today.year
            return _month_range(year, month_value)

    return None, None


def _parse_vendor(query: str) -> str | None:
    candidate = None
    normalized = query.lower()
    if "from" in normalized or "at" in normalized or "vendor" in normalized or "merchant" in normalized:
        match = re.search(
            r"\b(?:from|at|merchant|vendor)\s+([A-Za-z0-9&\-\.\s]{2,60}?)(?=(?:\s+in\b|\s+on\b|\s+for\b|\s+during\b|\s+between\b|\s+last\b|\s+this\b|$))",
            query,
            re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).strip(" .")

    if candidate:
        # remove leading month phrases such as "may at" or "june from"
        normalized_candidate = candidate.lower()
        month_names = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        for month in month_names:
            if normalized_candidate.startswith(month + " at "):
                candidate = candidate[len(month) + 4 :].strip()
                normalized_candidate = candidate.lower()
                break
            if normalized_candidate.startswith(month + " from "):
                candidate = candidate[len(month) + 6 :].strip()
                normalized_candidate = candidate.lower()
                break
            if normalized_candidate.startswith(month + " "):
                candidate = candidate[len(month) + 1 :].strip()
                normalized_candidate = candidate.lower()
                break
        if candidate and normalized_candidate not in {
            "last month",
            "this month",
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        }:
            return candidate
    return None


def parse_natural_search_filters(query: str) -> dict[str, date | str | None]:
    if not query.strip():
        return {"category": None, "vendor": None, "date_from": None, "date_to": None}

    normalized = query.lower()
    category = next(
        (cat for cat in CATEGORIES if cat.lower() in normalized),
        None,
    )
    if not category:
        kw_cat, _ = classify_by_keywords(query)
        category = kw_cat if kw_cat != "Miscellaneous" else None

    vendor = _parse_vendor(query)
    date_from, date_to = _parse_date_range(query)

    return {
        "category": category,
        "vendor": vendor,
        "date_from": date_from,
        "date_to": date_to,
    }


async def list_expenses(
    db: AsyncSession, user_id: int, filters: ExpenseFilter
) -> tuple[list[Expense], int]:
    base = select(Expense).order_by(Expense.created_at.desc())
    base = _apply_filters(base, user_id, filters)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    rows = await db.execute(base.offset(filters.skip).limit(filters.limit))
    return list(rows.scalars().all()), total


async def semantic_search(
    db: AsyncSession,
    user_id: int,
    query: str,
    skip: int = 0,
    limit: int = 20,
) -> list[Expense]:
    structured = parse_natural_search_filters(query)
    if structured["category"] or structured["vendor"] or structured["date_from"] or structured["date_to"]:
        stmt = select(Expense).where(Expense.user_id == user_id)
        if structured["category"]:
            stmt = stmt.where(
                Expense.category_name.ilike(f"%{structured['category']}%")
            )
        if structured["vendor"]:
            stmt = stmt.where(
                Expense.vendor_name.ilike(f"%{structured['vendor']}%")
            )
        if structured["date_from"]:
            stmt = stmt.where(Expense.expense_date >= structured["date_from"])
        if structured["date_to"]:
            stmt = stmt.where(Expense.expense_date <= structured["date_to"])
        stmt = stmt.order_by(Expense.created_at.desc()).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        if items:
            return items

    vector_hits = search_similar(query, user_id, n_results=limit + skip + 20)
    expense_ids: list[int] = []
    for hit in vector_hits:
        eid = hit.get("metadata", {}).get("expense_id")
        if eid:
            try:
                expense_ids.append(int(eid))
            except (TypeError, ValueError):
                continue

    if expense_ids:
        result = await db.execute(
            select(Expense).where(
                Expense.user_id == user_id,
                Expense.id.in_(expense_ids),
            )
        )
        by_id = {e.id: e for e in result.scalars().all()}
        ordered = [by_id[i] for i in expense_ids if i in by_id]
        return ordered[skip : skip + limit]

    stmt = (
        select(Expense)
        .where(
            Expense.user_id == user_id,
            (
                Expense.vendor_name.ilike(f"%{query}%")
                | Expense.category_name.ilike(f"%{query}%")
                | Expense.notes.ilike(f"%{query}%")
            ),
        )
        .order_by(Expense.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_summary(db: AsyncSession, user_id: int) -> ExpenseSummary:
    agg = await db.execute(
        select(
            func.coalesce(func.sum(Expense.total_amount), 0),
            func.count(Expense.id),
        ).where(Expense.user_id == user_id)
    )
    total_sum, count = agg.one()

    dup_count = (
        await db.execute(
            select(func.count(Expense.id)).where(
                Expense.user_id == user_id, Expense.is_duplicate.is_(True)
            )
        )
    ).scalar() or 0

    cat_rows = await db.execute(
        select(Expense.category_name, func.sum(Expense.total_amount))
        .where(Expense.user_id == user_id)
        .group_by(Expense.category_name)
    )
    by_category = {
        (r[0] or "Uncategorized"): Decimal(str(r[1] or 0)) for r in cat_rows.all()
    }

    vendor_rows = await db.execute(
        select(Expense.vendor_name, func.sum(Expense.total_amount))
        .where(Expense.user_id == user_id)
        .group_by(Expense.vendor_name)
        .limit(10)
    )
    by_vendor = {
        (r[0] or "Unknown"): Decimal(str(r[1] or 0)) for r in vendor_rows.all()
    }

    trend_rows = await db.execute(
        select(
            extract("year", Expense.expense_date),
            extract("month", Expense.expense_date),
            func.sum(Expense.total_amount),
        )
        .where(Expense.user_id == user_id, Expense.expense_date.isnot(None))
        .group_by(
            extract("year", Expense.expense_date),
            extract("month", Expense.expense_date),
        )
        .order_by(
            extract("year", Expense.expense_date),
            extract("month", Expense.expense_date),
        )
        .limit(12)
    )
    monthly_trend = [
        {
            "year": int(r[0]) if r[0] else None,
            "month": int(r[1]) if r[1] else None,
            "total": float(r[2] or 0),
        }
        for r in trend_rows.all()
    ]

    recent = await db.execute(
        select(Bill)
        .where(Bill.user_id == user_id)
        .order_by(Bill.created_at.desc())
        .limit(5)
    )
    recent_bills = [
        {
            "id": b.id,
            "filename": b.original_filename,
            "status": b.status.value,
            "created_at": b.created_at.isoformat(),
        }
        for b in recent.scalars().all()
    ]

    return ExpenseSummary(
        total_expenses=Decimal(str(total_sum)),
        expense_count=count,
        by_category=by_category,
        by_vendor=by_vendor,
        monthly_trend=monthly_trend,
        duplicate_count=dup_count,
        recent_bills=recent_bills,
    )
