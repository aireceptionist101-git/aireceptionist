import json
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
    """
    Receives all Vapi.ai webhook events.
    Logs raw payload for every event.
    Only processes `end-of-call-report`; all other types are acknowledged and ignored.
    """
    if settings.WEBHOOK_SECRET:
        incoming_secret = request.headers.get("x-vapi-secret", "")
        if incoming_secret != settings.WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret",
            )

    raw_body = await request.json()
    message = raw_body.get("message", {})
    event_type = message.get("type", "unknown")
    call_data = message.get("call", {})
    call_id = call_data.get("id", "N/A")

    # Log full raw payload for every event
    logger.info(
        "Webhook received | event=%s | call_id=%s | raw_payload=%s",
        event_type, call_id, json.dumps(raw_body, indent=2, default=str),
    )

    if event_type not in HANDLED_EVENT_TYPES:
        logger.info("Skipping event | event=%s | call_id=%s", event_type, call_id)
        return {"received": True, "processed": False, "type": event_type}

    # Parse into Pydantic model for DB processing
    payload = VapiWebhookPayload(**raw_body)

    if payload.message.call is None:
        logger.warning("Rejected event | event=%s | reason=missing call data", event_type)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end-of-call-report missing call data",
        )

    call = payload.message.call
    artifact = payload.message.artifact
    analysis = payload.message.analysis

    logger.info(
        "Processing end-of-call-report | call_id=%s | status=%s | duration=%s | cost=%s | ended_reason=%s",
        call_id, call.status, call.duration, call.cost, call.endedReason,
    )
    logger.info(
        "Artifact data | call_id=%s | transcript_length=%s | recording_url=%s",
        call_id,
        len(artifact.transcript) if artifact and artifact.transcript else 0,
        artifact.recordingUrl if artifact else None,
    )
    logger.info(
        "Analysis data | call_id=%s | summary=%s | success=%s | structured_data=%s",
        call_id,
        (analysis.summary[:100] + "...") if analysis and analysis.summary and len(analysis.summary) > 100 else (analysis.summary if analysis else None),
        analysis.successEvaluation if analysis else None,
        analysis.structuredData if analysis else None,
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
