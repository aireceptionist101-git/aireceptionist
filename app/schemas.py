from datetime import datetime
from typing import Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Webhook payload schemas (inbound from Vapi.ai)
# ---------------------------------------------------------------------------

class VapiCallPayload(BaseModel):
    id: str
    orgId: str | None = None
    assistantId: str | None = None
    status: str | None = None
    startedAt: datetime | None = None
    endedAt: datetime | None = None
    duration: float | None = None
    cost: float | None = None
    endedReason: str | None = None


class VapiArtifactPayload(BaseModel):
    transcript: str | None = None
    recordingUrl: str | None = None
    stereoRecordingUrl: str | None = None


class VapiAnalysisPayload(BaseModel):
    summary: str | None = None
    successEvaluation: str | None = None
    structuredData: dict[str, Any] | None = None


class VapiMessagePayload(BaseModel):
    type: str
    call: VapiCallPayload | None = None
    artifact: VapiArtifactPayload | None = None
    analysis: VapiAnalysisPayload | None = None


class VapiWebhookPayload(BaseModel):
    message: VapiMessagePayload


# ---------------------------------------------------------------------------
# API response schemas (outbound to dashboard)
# ---------------------------------------------------------------------------

class CallReportResponse(BaseModel):
    call_id: str
    org_id: str | None
    assistant_id: str | None
    status: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None
    cost: float | None
    ended_reason: str | None
    transcript: str | None
    recording_url: str | None
    stereo_recording_url: str | None
    summary: str | None
    success_evaluation: str | None
    structured_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedCallsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[CallReportResponse]
