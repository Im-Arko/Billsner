"""Export reports to CSV, Excel, and PDF."""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.schemas.expense import ExpenseFilter


async def fetch_expenses_for_export(
    db: AsyncSession, user_id: int, filters: ExpenseFilter
) -> list[dict]:
    conditions = [Expense.user_id == user_id]
    if filters.category:
        conditions.append(Expense.category_name.ilike(f"%{filters.category}%"))
    if filters.date_from:
        conditions.append(Expense.expense_date >= filters.date_from)
    if filters.date_to:
        conditions.append(Expense.expense_date <= filters.date_to)

    if filters.vendor:
        conditions.append(Expense.vendor_name.ilike(f"%{filters.vendor}%"))

    result = await db.execute(
        select(Expense).where(and_(*conditions)).order_by(Expense.expense_date.desc())
    )
    rows = []
    for e in result.scalars().all():
        rows.append(
            {
                "id": e.id,
                "vendor": e.vendor_name,
                "bill_number": e.bill_number,
                "amount": float(e.total_amount or 0),
                "tax": float(e.tax_amount or 0),
                "category": e.category_name,
                "date": e.expense_date.isoformat() if e.expense_date else "",
                "currency": e.currency,
                "payment_method": e.payment_method,
                "duplicate": e.is_duplicate,
            }
        )
    return rows


def export_csv(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def export_excel(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Expenses")
    return buf.getvalue()


def export_pdf(rows: list[dict], title: str = "Expense Report") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"])]

    if not rows:
        elements.append(Paragraph("No expenses found.", styles["Normal"]))
    else:
        headers = list(rows[0].keys())
        data = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows[:100]]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(table)

    doc.build(elements)
    return buf.getvalue()
