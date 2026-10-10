from datetime import datetime
from sqlalchemy import Float, ForeignKey, String, Text, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base

class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    input_type: Mapped[str] = mapped_column(String(10))
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str] = mapped_column(String(20))
    confidence_score: Mapped[float] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class GuestUsage(Base):
    __tablename__ = "guest_usages"

    identifier: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
