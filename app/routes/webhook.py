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
def receive_webhook(
    payload: VapiWebhookPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receives all Vapi.ai webhook events.
    Only processes `end-of-call-report`; all other types are acknowledged and ignored.
    """
    if settings.WEBHOOK_SECRET:
        incoming_secret = request.headers.get("x-vapi-secret", "")
        if incoming_secret != settings.WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret",
            )

    event_type = payload.message.type

    if event_type not in HANDLED_EVENT_TYPES:
        logger.info("Ignoring webhook event type: %s", event_type)
        return {"received": True, "processed": False, "type": event_type}

    if payload.message.call is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end-of-call-report missing call data",
        )

    try:
        report = upsert_call_report(db, payload)
        logger.info("Upserted call report: %s", report.call_id)
    except Exception as exc:
        logger.exception("Failed to persist call report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist call report",
        ) from exc

    return {"received": True, "processed": True, "call_id": report.call_id}
