import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import upsert_call_report
from app.database import get_db
from app.schemas import VapiWebhookPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

HANDLED_EVENT_TYPES = {"end-of-call-report"}


@router.post("", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()
    if not body:
        return {"received": True, "processed": False, "reason": "empty body"}

    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    message = raw_body.get("message", {})
    event_type = message.get("type", "unknown")
    call_id = message.get("call", {}).get("id", "N/A")

    if settings.WEBHOOK_SECRET:
        incoming_secret = request.headers.get("x-vapi-secret", "")
        if incoming_secret != settings.WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret",
            )

    if event_type not in HANDLED_EVENT_TYPES:
        return {"received": True, "processed": False, "type": event_type}

    try:
        payload = VapiWebhookPayload(**raw_body)
    except Exception as exc:
        logger.exception("Payload validation failed | call_id=%s | error=%s", call_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {str(exc)[:200]}",
        ) from exc

    if payload.message.call is None:
        logger.warning("end-of-call-report missing call data | call_id=%s", call_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end-of-call-report missing call data",
        )

    msg = payload.message
    analysis = msg.analysis

    logger.info(
        "end-of-call-report | call_id=%s | duration=%.1fs | cost=$%.4f | ended_reason=%s | started=%s | ended=%s | summary=%s | success=%s",
        call_id,
        msg.durationSeconds or 0,
        msg.cost or 0,
        msg.endedReason,
        msg.startedAt,
        msg.endedAt,
        (analysis.summary[:80] + "...") if analysis and analysis.summary and len(analysis.summary) > 80 else (analysis.summary if analysis else None),
        analysis.successEvaluation if analysis else None,
    )

    try:
        report = upsert_call_report(db, payload)
        logger.info("Saved to DB | call_id=%s", report.call_id)
    except Exception as exc:
        logger.exception("DB save failed | call_id=%s | error=%s", call_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist call report",
        ) from exc

    return {"received": True, "processed": True, "call_id": report.call_id}
