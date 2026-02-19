from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import get_call_reports
from app.database import get_db
from app.models import CallReport
from app.schemas import CallReportResponse, PaginatedCallsResponse

AEST = ZoneInfo("Australia/Sydney")

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("", response_model=PaginatedCallsResponse)
def list_calls(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=500, description="Records per page (max 500)"),
    search: str | None = Query(default=None, description="Search in transcript, summary, ended_reason"),
    date_from: datetime | None = Query(default=None, description="Filter calls started on or after this datetime (ISO 8601)"),
    date_to: datetime | None = Query(default=None, description="Filter calls started on or before this datetime (ISO 8601)"),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of call reports for the dashboard.

    Defaults to the last 30 days when no date range is provided.
    Supports:
    - Pagination via `page` and `page_size`
    - Full-text search across transcript, summary, and ended_reason
    - Date range filtering via `date_from` and `date_to`
    """
    if date_from is None and date_to is None:
        date_from = datetime.now(AEST) - timedelta(days=30)

    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`date_from` must be before `date_to`",
        )

    total, records = get_call_reports(
        db,
        page=page,
        page_size=page_size,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

    return PaginatedCallsResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=[CallReportResponse.model_validate(r) for r in records],
    )


@router.get("/{call_id}", response_model=CallReportResponse)
def get_call(call_id: str, db: Session = Depends(get_db)):
    """Returns a single call report by Vapi call ID."""
    record = db.execute(
        select(CallReport).where(CallReport.call_id == call_id)
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    return CallReportResponse.model_validate(record)
