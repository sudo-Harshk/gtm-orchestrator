from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.groq_client import groq_client, GroqOperationalError
from app.logger import get_logger
from app.schemas import ErrorResponse, LeadInput, ReviewResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/review")
async def review_lead(request: Request, lead: LeadInput) -> ReviewResponse | ErrorResponse:
    """
    Review a lead using Groq LLM with structured output.

    Accepts nested GTM lead payloads.
    Validates on first /review call if GROQ_API_KEY is missing.
    """
    request_id = request.headers.get("X-Request-Id", "-")
    lead_id = lead.lead_id

    start_time = time.time()

    logger.info(
        "review_started",
        extra={
            "request_id": request_id,
            "lead_id": lead_id,
        },
    )

    try:
        if not lead.lead_id:
            logger.error(
                "invalid_payload",
                extra={"request_id": request_id, "reason": "missing_lead_id"},
            )
            raise HTTPException(status_code=400, detail="lead_id is required")

        # Convert lead to dict for Groq client
        lead_dict = lead.model_dump()

        # Call Groq inference
        review_result = groq_client.review_lead(lead_dict)
        latency_ms = int((time.time() - start_time) * 1000)

        response = ReviewResponse(
            request_id=request_id,
            lead_id=lead_id,
            confidence=review_result["confidence"],
            rationale=review_result["rationale"],
            strategy=review_result["strategy"],
            suggested_email_open=review_result["suggested_email_open"],
            model="llama-3.3-70b-versatile",
            latency_ms=latency_ms,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            "review_completed",
            extra={
                "request_id": request_id,
                "lead_id": lead_id,
                "latency_ms": latency_ms,
                "confidence": response.confidence,
                "model": response.model,
            },
        )

        return response

    except GroqOperationalError as e:
        """Handle typed Groq operational errors."""
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "groq_operational_error",
            extra={
                "request_id": request_id,
                "lead_id": lead_id,
                "error_type": e.error_type.value,
                "error_message": e.message,
                "latency_ms": latency_ms,
            },
        )
        return ErrorResponse(
            status="failed",
            reason=e.error_type.value,
            request_id=request_id,
            details=e.message,
            error_type=e.error_type.value,
        )

    except ValueError as e:
        """Handle validation errors."""
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "review_validation_failed",
            extra={
                "request_id": request_id,
                "lead_id": lead_id,
                "error": str(e),
                "latency_ms": latency_ms,
                "error_type": "validation_error",
            },
        )
        return ErrorResponse(
            status="failed",
            reason="validation_failed",
            request_id=request_id,
            details=str(e),
            error_type="validation_error",
        )

    except Exception as e:
        """Handle unexpected errors."""
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "review_failed",
            extra={
                "request_id": request_id,
                "lead_id": lead_id,
                "error": str(e),
                "latency_ms": latency_ms,
                "error_type": "internal_error",
            },
        )
        return ErrorResponse(
            status="failed",
            reason="internal_error",
            request_id=request_id,
            details="Internal server error",
            error_type="internal_error",
        )
