from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CallReport(Base):
    """Stores one row per end-of-call-report webhook received from Vapi.ai."""

    __tablename__ = "call_reports"

    # Primary key — use Vapi's call id as the natural key to allow safe upserts
    call_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # call.*
    org_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assistant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    ended_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # artifact.*
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stereo_recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # analysis.*
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_evaluation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # caller info
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # structured outputs (extracted by Vapi LLM after call)
    caller_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason_for_call: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_successful: Mapped[bool | None] = mapped_column(nullable=True)
    transfer_destination: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # housekeeping
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
