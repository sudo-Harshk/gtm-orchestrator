from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Domain Models: GTM Lead Architecture
# ============================================================================


class CompanyInfo(BaseModel):
    """Company-level context for lead routing and assessment."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Northwind Health Analytics",
        "domain": "northwindhealth.io",
        "employee_count": 185,
        "revenue_band": "$25M-$50M",
        "industry": "healthcare SaaS"
    }})

    name: str = Field(..., description="Company legal name")
    domain: str = Field(..., description="Company domain")
    employee_count: Optional[int] = Field(None, description="Estimated headcount")
    revenue_band: Optional[str] = Field(None, description="Revenue range bracket")
    industry: Optional[str] = Field(None, description="Industry classification")


class ContactInfo(BaseModel):
    """Contact-level profile for outreach targeting."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "first_name": "Maya",
        "last_name": "Patel",
        "title": "VP of Revenue Operations",
        "email": "maya.patel@northwindhealth.io",
        "linkedin_url": "https://www.linkedin.com/in/mayapatel"
    }})

    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    title: str = Field(..., description="Job title")
    email: str = Field(..., description="Business email address")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")


class RoutingInfo(BaseModel):
    """Routing and segmentation metadata."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "owner": "outbound-pipeline",
        "source": "apollo",
        "segment": "healthcare-saas-midmarket"
    }})

    owner: Optional[str] = Field(None, description="Team/workflow owner")
    source: Optional[str] = Field(None, description="Data source (apollo, clearbit, etc.)")
    segment: Optional[str] = Field(None, description="Market segment")


class SignalInfo(BaseModel):
    """Behavioral and contextual signals for lead scoring."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "recent_funding": True,
        "hiring_activity": ["revops-manager", "sales-development-rep"],
        "tech_stack": ["salesforce", "hubspot", "snowflake"],
        "notes": "Expanding outbound motion across provider and payer verticals."
    }})

    recent_funding: Optional[bool] = Field(None, description="Recent funding event detected")
    hiring_activity: Optional[list[str]] = Field(None, description="Recent job openings")
    tech_stack: Optional[list[str]] = Field(None, description="Known tech stack")
    notes: Optional[str] = Field(None, description="Free-form signal notes")


class LeadState(BaseModel):
    """Current operational state of the lead."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "queued",
        "created_at": "2026-05-12T08:14:00Z"
    }})

    status: str = Field(default="queued", description="Current lead status")
    created_at: Optional[str] = Field(None, description="ISO8601 timestamp")


class LeadInput(BaseModel):
    """Complete GTM lead payload with nested domain structure."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "lead_id": "lead_20260512_0142",
        "company": {
            "name": "Northwind Health Analytics",
            "domain": "northwindhealth.io",
            "employee_count": 185,
            "revenue_band": "$25M-$50M",
            "industry": "healthcare SaaS"
        },
        "contact": {
            "first_name": "Maya",
            "last_name": "Patel",
            "title": "VP of Revenue Operations",
            "email": "maya.patel@northwindhealth.io"
        },
        "routing": {
            "source": "apollo",
            "segment": "healthcare-saas-midmarket"
        },
        "signals": {
            "recent_funding": True,
            "tech_stack": ["salesforce", "hubspot"]
        },
        "state": {
            "status": "queued"
        }
    }})

    lead_id: str = Field(..., description="Unique lead identifier")
    company: CompanyInfo = Field(..., description="Company information")
    contact: ContactInfo = Field(..., description="Contact information")
    routing: Optional[RoutingInfo] = Field(default_factory=RoutingInfo, description="Routing metadata")
    signals: Optional[SignalInfo] = Field(default_factory=SignalInfo, description="Signal data")
    state: Optional[LeadState] = Field(default_factory=LeadState, description="Lead state")


# ============================================================================
# API Response Models
# ============================================================================


class ReviewResponse(BaseModel):
    """Structured review result from inference."""

    request_id: str = Field(..., description="Request tracing ID")
    lead_id: str = Field(..., description="Lead identifier")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    rationale: str = Field(..., description="Operational assessment rationale")
    strategy: str = Field(..., description="Suggested outreach strategy")
    suggested_email_open: str = Field(..., description="Suggested email opening line")
    model: str = Field(..., description="Model used for inference")
    latency_ms: int = Field(..., description="Inference latency in milliseconds")
    reviewed_at: str = Field(..., description="ISO8601 timestamp of review")


class ErrorResponse(BaseModel):
    """Typed operational error response."""

    status: str = Field(default="failed", description="Response status")
    reason: str = Field(..., description="Machine-readable error code")
    request_id: str = Field(..., description="Request tracing ID")
    details: Optional[str] = Field(None, description="Optional additional context")
    error_type: Optional[str] = Field(None, description="Error category")
