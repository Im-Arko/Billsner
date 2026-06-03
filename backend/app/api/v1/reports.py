from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.expense import ExpenseFilter
from app.services.report_service import (
    export_csv,
    export_excel,
    export_pdf,
    fetch_expenses_for_export,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/export")
async def export_report(
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    category: str | None = None,
    vendor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type

    filters = ExpenseFilter(
        category=category,
        vendor=vendor,
        date_from=date_type.fromisoformat(date_from) if date_from else None,
        date_to=date_type.fromisoformat(date_to) if date_to else None,
        limit=10000,
    )
    rows = await fetch_expenses_for_export(db, current_user.id, filters)

    if format == "csv":
        content = export_csv(rows)
        media = "text/csv"
        filename = "expenses.csv"
    elif format == "xlsx":
        content = export_excel(rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "expenses.xlsx"
    else:
        content = export_pdf(rows)
        media = "application/pdf"
        filename = "expenses.pdf"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
