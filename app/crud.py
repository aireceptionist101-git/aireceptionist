from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import CallReport
from app.schemas import VapiArtifactPayload, VapiAnalysisPayload, VapiWebhookPayload

AEST = ZoneInfo("Australia/Sydney")


def upsert_call_report(db: Session, payload: VapiWebhookPayload) -> CallReport:
    """
    Insert or update a call_report row from a Vapi end-of-call-report payload.
    Uses PostgreSQL ON CONFLICT DO UPDATE so re-delivered webhooks are idempotent.
    """
    msg = payload.message
    call = msg.call
    artifact = msg.artifact or VapiArtifactPayload()
    analysis = msg.analysis or VapiAnalysisPayload()

    def to_aest(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        # ensure timezone-aware before converting
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(AEST)

    values = {
        "call_id": call.id,
        "org_id": call.orgId,
        "assistant_id": call.assistantId,
        "status": call.status,
        "started_at": to_aest(call.startedAt),
        "ended_at": to_aest(call.endedAt),
        "duration_seconds": call.duration,
        "cost": call.cost,
        "ended_reason": call.endedReason,
        "transcript": artifact.transcript,
        "recording_url": artifact.recordingUrl,
        "stereo_recording_url": artifact.stereoRecordingUrl,
        "summary": analysis.summary,
        "success_evaluation": analysis.successEvaluation,
        "structured_data": analysis.structuredData,
        "updated_at": datetime.now(AEST),
    }

    stmt = (
        pg_insert(CallReport)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["call_id"],
            set_={k: v for k, v in values.items() if k != "call_id"},
        )
        .returning(CallReport)
    )

    result = db.execute(stmt)
    db.commit()
    return result.scalars().one()


def get_call_reports(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[int, list[CallReport]]:
    """
    Return (total_count, records) with optional full-text search across
    transcript / summary / ended_reason, and date range filters.
    """
    query = select(CallReport)

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                CallReport.transcript.ilike(term),
                CallReport.summary.ilike(term),
                CallReport.ended_reason.ilike(term),
            )
        )

    if date_from:
        query = query.where(CallReport.started_at >= date_from)

    if date_to:
        query = query.where(CallReport.started_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    records = (
        db.execute(
            query.order_by(CallReport.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    return total, records
