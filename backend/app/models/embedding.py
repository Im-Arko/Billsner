"""Metadata linking bills to the embedded text similarity index."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BillEmbedding(Base):
    __tablename__ = "bill_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(
        ForeignKey("bills.id"), unique=True, index=True
    )
    chroma_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    collection_name: Mapped[str] = mapped_column(String(100), default="bills")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bill: Mapped["Bill"] = relationship(back_populates="embedding")
