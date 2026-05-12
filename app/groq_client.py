from __future__ import annotations

import json
from enum import Enum
from typing import Optional

from groq import Groq, APIConnectionError, APIStatusError

from app.config import config
from app.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Operational Error Types
# ============================================================================


class GroqErrorType(str, Enum):
    """Machine-readable Groq operational error taxonomy."""

    MISSING_API_KEY = "missing_api_key"
    AUTH_FAILED = "groq_auth_failed"
    TIMEOUT = "groq_timeout"
    RATE_LIMITED = "groq_rate_limited"
    CONNECTION_FAILED = "groq_connection_failed"
    INVALID_MODEL = "invalid_model"
    MALFORMED_REQUEST = "malformed_request"
    INVALID_JSON_RESPONSE = "invalid_json_response"
    MISSING_FIELDS = "missing_required_fields"


class GroqOperationalError(Exception):
    """Typed operational error from Groq inference."""

    def __init__(
        self,
        error_type: GroqErrorType,
        message: str,
        details: Optional[dict] = None,
    ):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_response_dict(self) -> dict:
        """Convert to API error response format."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
# Groq Client with Infrastructure-Grade Error Handling
# ============================================================================


class GroqClient:
    """Production Groq inference client with typed operational errors."""

    def __init__(self):
        """Initialize without API key - validate on first inference call."""
        self.client: Optional[Groq] = None
        self.api_key: Optional[str] = None
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.1
        self.max_tokens = 300
        self._api_key_validated = False

    def _ensure_api_key(self) -> None:
        """
        Validate and initialize Groq client on first inference.

        Timing: Called on first /review request, NOT during startup.
        """
        if self._api_key_validated:
            return

        api_key = config.groq_api_key
        if not api_key:
            logger.error(
                "groq_missing_api_key",
                extra={"error_type": GroqErrorType.MISSING_API_KEY.value},
            )
            raise GroqOperationalError(
                GroqErrorType.MISSING_API_KEY,
                "GROQ_API_KEY environment variable not set",
            )

        try:
            self.client = Groq(api_key=api_key)
            self.api_key = api_key
            self._api_key_validated = True
            logger.info("groq_client_initialized")
        except Exception as e:
            logger.error(
                "groq_initialization_failed",
                extra={
                    "error": str(e),
                    "error_type": GroqErrorType.AUTH_FAILED.value,
                },
            )
            raise GroqOperationalError(
                GroqErrorType.AUTH_FAILED,
                f"Failed to initialize Groq client: {str(e)}",
            ) from e

    def review_lead(self, lead: dict) -> dict:
        """
        Review a lead using Groq LLM with structured JSON output.

        Args:
            lead: Lead object with nested structure

        Returns:
            Dict with keys: confidence, rationale, strategy, suggested_email_open

        Raises:
            GroqOperationalError: Typed operational failure
        """
        # Ensure API key is initialized on first call
        self._ensure_api_key()

        prompt = self._build_review_prompt(lead)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            response_text = response.choices[0].message.content
            return self._parse_and_validate_response(response_text)

        except GroqOperationalError:
            # Re-raise already-typed errors
            raise

        except APIStatusError as e:
            # Handle authentication and rate limiting
            if e.status_code == 401:
                logger.error(
                    "groq_auth_failed",
                    extra={
                        "status_code": e.status_code,
                        "error_type": GroqErrorType.AUTH_FAILED.value,
                    },
                )
                raise GroqOperationalError(
                    GroqErrorType.AUTH_FAILED,
                    f"Groq authentication failed: {str(e)}",
                ) from e
            elif e.status_code == 429:
                logger.error(
                    "groq_rate_limited",
                    extra={
                        "status_code": e.status_code,
                        "error_type": GroqErrorType.RATE_LIMITED.value,
                    },
                )
                raise GroqOperationalError(
                    GroqErrorType.RATE_LIMITED,
                    "Groq API rate limit exceeded",
                ) from e
            elif e.status_code == 400:
                logger.error(
                    "groq_invalid_request",
                    extra={
                        "status_code": e.status_code,
                        "error_type": GroqErrorType.MALFORMED_REQUEST.value,
                        "error": str(e),
                    },
                )
                raise GroqOperationalError(
                    GroqErrorType.MALFORMED_REQUEST,
                    f"Invalid Groq request: {str(e)}",
                ) from e
            else:
                logger.error(
                    "groq_api_error",
                    extra={
                        "status_code": e.status_code,
                        "error_type": GroqErrorType.CONNECTION_FAILED.value,
                        "error": str(e),
                    },
                )
                raise GroqOperationalError(
                    GroqErrorType.CONNECTION_FAILED,
                    f"Groq API error: {str(e)}",
                ) from e

        except APIConnectionError as e:
            logger.error(
                "groq_connection_failed",
                extra={
                    "error_type": GroqErrorType.CONNECTION_FAILED.value,
                    "error": str(e),
                },
            )
            raise GroqOperationalError(
                GroqErrorType.CONNECTION_FAILED,
                f"Groq connection failed: {str(e)}",
            ) from e

        except Exception as e:
            logger.error(
                "groq_inference_failed",
                extra={
                    "error_type": "unknown",
                    "error": str(e),
                },
            )
            raise

    def _build_review_prompt(self, lead: dict) -> str:
        """
        Construct operationally explicit review prompt from nested lead structure.

        The prompt is built from explicit domain sections rather than raw payload
        dumping, improving semantic clarity, auditability, and future extensibility.
        """
        # Extract domain contexts from nested structure
        company_section = self._build_company_context(lead.get("company", {}))
        contact_section = self._build_contact_context(lead.get("contact", {}))
        signals_section = self._build_signals_context(lead.get("signals", {}))
        routing_section = self._build_routing_context(lead.get("routing", {}))
        state_section = self._build_state_context(lead.get("state", {}))

        # Construct prompt from explicit operational GTM briefing sections
        prompt = f"""You are a lead review system for healthcare SaaS outbound operations.
Review the following prospect and return ONLY valid JSON with no markdown or prose.

{company_section}

{contact_section}

{signals_section}

{routing_section}

{state_section}

Return exactly this JSON structure with no additional text:
{{
  "confidence": <integer 0-100>,
  "rationale": "<2-3 sentence operational assessment>",
  "strategy": "<1-2 sentence outreach strategy>",
  "suggested_email_open": "<suggested email opening line>"
}}"""

        return prompt

    def _build_company_context(self, company: dict) -> str:
        """
        Build Company Context section from domain model.

        Extracts and formats company-level information:
        name, domain, industry, employee count, revenue band.
        """
        if not company:
            return "COMPANY CONTEXT\nNo company information available"

        lines = ["COMPANY CONTEXT"]

        name = company.get("name")
        if name:
            lines.append(f"Name: {name}")

        domain = company.get("domain")
        if domain:
            lines.append(f"Domain: {domain}")

        industry = company.get("industry")
        if industry:
            lines.append(f"Industry: {industry}")

        employee_count = company.get("employee_count")
        if employee_count:
            lines.append(f"Employee Count: {employee_count}")

        revenue_band = company.get("revenue_band")
        if revenue_band:
            lines.append(f"Revenue Band: {revenue_band}")

        return "\n".join(lines) if len(lines) > 1 else "COMPANY CONTEXT\nNo company information available"

    def _build_contact_context(self, contact: dict) -> str:
        """
        Build Contact Context section from domain model.

        Extracts and formats contact-level information:
        name, title, email, linkedin profile.
        """
        if not contact:
            return "CONTACT CONTEXT\nNo contact information available"

        lines = ["CONTACT CONTEXT"]

        first_name = contact.get("first_name", "").strip()
        last_name = contact.get("last_name", "").strip()
        if first_name or last_name:
            name = f"{first_name} {last_name}".strip()
            lines.append(f"Name: {name}")

        title = contact.get("title")
        if title:
            lines.append(f"Title: {title}")

        email = contact.get("email")
        if email:
            lines.append(f"Email: {email}")

        linkedin_url = contact.get("linkedin_url")
        if linkedin_url:
            lines.append(f"LinkedIn: {linkedin_url}")

        return "\n".join(lines) if len(lines) > 1 else "CONTACT CONTEXT\nNo contact information available"

    def _build_signals_context(self, signals: dict) -> str:
        """
        Build Operational Signals section from domain model.

        Extracts and formats behavioral/contextual signals:
        funding activity, hiring, tech stack, enrichment notes.
        """
        if not signals:
            return "OPERATIONAL SIGNALS\nNo signals available"

        lines = ["OPERATIONAL SIGNALS"]

        if signals.get("recent_funding"):
            lines.append("- Recent funding activity detected")

        hiring_activity = signals.get("hiring_activity")
        if hiring_activity:
            if isinstance(hiring_activity, list) and hiring_activity:
                activities = ", ".join(str(h) for h in hiring_activity[:3])
                lines.append(f"- Hiring Activity: {activities}")
            elif hiring_activity:
                lines.append(f"- Hiring Activity: {hiring_activity}")

        tech_stack = signals.get("tech_stack")
        if tech_stack:
            if isinstance(tech_stack, list) and tech_stack:
                techs = ", ".join(str(t) for t in tech_stack[:4])
                lines.append(f"- Tech Stack: {techs}")
            elif tech_stack:
                lines.append(f"- Tech Stack: {tech_stack}")

        notes = signals.get("notes")
        if notes and isinstance(notes, str) and notes.strip():
            truncated_notes = notes[:120].strip()
            lines.append(f"- Notes: {truncated_notes}")

        return "\n".join(lines) if len(lines) > 1 else "OPERATIONAL SIGNALS\nNo signals available"

    def _build_routing_context(self, routing: dict) -> str:
        """
        Build Routing Metadata section from domain model.

        Extracts and formats routing/segmentation information:
        source, segment, owner.
        """
        if not routing:
            return "ROUTING METADATA\nNo routing metadata available"

        lines = ["ROUTING METADATA"]

        source = routing.get("source")
        if source:
            lines.append(f"Source: {source}")

        segment = routing.get("segment")
        if segment:
            lines.append(f"Segment: {segment}")

        owner = routing.get("owner")
        if owner:
            lines.append(f"Owner: {owner}")

        return "\n".join(lines) if len(lines) > 1 else "ROUTING METADATA\nNo routing metadata available"

    def _build_state_context(self, state: dict) -> str:
        """
        Build Workflow State section from domain model.

        Extracts and formats workflow operational state:
        current status, creation timestamp.
        """
        if not state:
            return "WORKFLOW STATE\nNo state information available"

        lines = ["WORKFLOW STATE"]

        status = state.get("status")
        if status:
            lines.append(f"Current Status: {status}")

        created_at = state.get("created_at")
        if created_at:
            lines.append(f"Created: {created_at}")

        return "\n".join(lines) if len(lines) > 1 else "WORKFLOW STATE\nNo state information available"

    def _parse_and_validate_response(self, response_text: str) -> dict:
        """
        Parse and validate JSON response from model.

        Ensures:
        - Valid JSON format
        - All required fields present
        - Proper field types and ranges

        Raises:
            GroqOperationalError: On parse or validation failure
        """
        # Parse JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(
                "invalid_json_from_model",
                extra={
                    "raw_response": response_text[:200],
                    "error_type": GroqErrorType.INVALID_JSON_RESPONSE.value,
                    "error": str(e),
                },
            )
            raise GroqOperationalError(
                GroqErrorType.INVALID_JSON_RESPONSE,
                f"Model returned invalid JSON: {str(e)}",
                details={"raw_response": response_text[:200]},
            ) from e

        # Validate required fields
        required_fields = {"confidence", "rationale", "strategy", "suggested_email_open"}
        missing = required_fields - set(data.keys())
        if missing:
            logger.error(
                "missing_response_fields",
                extra={
                    "missing_fields": list(missing),
                    "error_type": GroqErrorType.MISSING_FIELDS.value,
                },
            )
            raise GroqOperationalError(
                GroqErrorType.MISSING_FIELDS,
                f"Missing required fields: {missing}",
                details={"missing": list(missing)},
            )

        # Validate field types and ranges
        if not isinstance(data.get("confidence"), int):
            logger.error(
                "invalid_confidence_type",
                extra={
                    "error_type": GroqErrorType.INVALID_JSON_RESPONSE.value,
                    "received_type": type(data.get("confidence")).__name__,
                },
            )
            raise GroqOperationalError(
                GroqErrorType.INVALID_JSON_RESPONSE,
                "confidence must be an integer",
            )

        confidence = data.get("confidence")
        if not 0 <= confidence <= 100:
            logger.error(
                "confidence_out_of_range",
                extra={
                    "error_type": GroqErrorType.INVALID_JSON_RESPONSE.value,
                    "confidence": confidence,
                },
            )
            raise GroqOperationalError(
                GroqErrorType.INVALID_JSON_RESPONSE,
                f"confidence must be between 0-100, got {confidence}",
            )

        logger.info("response_validation_passed")
        return data


# Global client instance - initialized on first /review call
groq_client = GroqClient()
