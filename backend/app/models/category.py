"""Expense category lookup."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    keywords: Mapped[str | None] = mapped_column(String(500), nullable=True)

    expenses: Mapped[list["Expense"]] = relationship(back_populates="category")
