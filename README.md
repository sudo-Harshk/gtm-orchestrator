# gtm-orchestrator

An internal GTM workflow orchestration platform for healthcare SaaS outbound operations. Phase 2 establishes infrastructure-grade operational typing, deterministic AI review workflows, and nested domain architecture for realistic lead ingestion and assessment.

## Architecture

- **FastAPI worker** for local and containerized API execution
- **Nested domain models** for Apollo-style GTM lead payloads
- **Groq LLM integration** with llama-3.3-70b-versatile for deterministic lead review
- **Infrastructure-grade error typing** for operational disambiguation
- **Structured logging** with request context support and error categorization
- **Docker Compose** for reproducible local startup

## Phase Status

**Phase 2:** Intelligence Core + Schema Refinement + Operational Hardening ✓
- Groq integration with structured inference
- **Nested Pydantic domain models** (CompanyInfo, ContactInfo, RoutingInfo, SignalInfo, LeadState)
- Schema-validated lead review endpoint with Apollo-compatible payloads
- **Deterministic JSON responses** with validation contracts
- **Typed operational errors** distinguishing auth, timeout, rate-limit, malformed JSON, etc.
- **API key validation on first inference call** (not during startup)
- Request-aware logging with error_type and operational context

## Architecture Decisions

### Nested Domain Models

The system models GTM lead payloads with realistic nested structure:

```
LeadInput
├── lead_id (unique identifier)
├── company: CompanyInfo
│   ├── name (required)
│   ├── domain
│   ├── employee_count
│   ├── revenue_band
│   └── industry
├── contact: ContactInfo
│   ├── first_name (required)
│   ├── last_name (required)
│   ├── title (required)
│   ├── email (required)
│   └── linkedin_url
├── routing: RoutingInfo (optional)
│   ├── owner
│   ├── source
│   └── segment
├── signals: SignalInfo (optional)
│   ├── recent_funding
│   ├── hiring_activity
│   ├── tech_stack
│   └── notes
└── state: LeadState (optional)
    ├── status
    └── created_at
```

This structure is:
- **Strongly typed** with required/optional field discipline
- **Extensible** for future enrichment layers
- **Realistic** for Apollo-style and enrichment vendor ingestion
- **Infrastructure-oriented** for production middleware operations

### Operational Error Taxonomy

The system distinguishes these Groq operational failures:

- `missing_api_key`: GROQ_API_KEY environment variable not set
- `groq_auth_failed`: Authentication failure (401)
- `groq_rate_limited`: API rate limit exceeded (429)
- `groq_timeout`: Request timeout
- `groq_connection_failed`: Network/connection error
- `invalid_model`: Invalid model name or model not found
- `malformed_request`: Invalid API request (400)
- `invalid_json_response`: Model output is not valid JSON
- `missing_required_fields`: Model output missing required fields

Error responses are typed and predictable:

```json
{
  "status": "failed",
  "reason": "groq_rate_limited",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": "Groq API rate limit exceeded",
  "error_type": "groq_rate_limited"
}
```

### Deterministic Validation Guarantees

- All payloads are validated against strict Pydantic schemas
- Invalid types, missing required fields, and schema violations are rejected at API boundary
- Model responses are validated for structure, required fields, and value ranges
- Malformed JSON from inference is treated as operational failure, not accepted response
- Logging includes error categorization for operational diagnosis

## Quick Start

1. Copy `.env.example` to `.env` and set `GROQ_API_KEY`.
2. Run `docker compose up --build`.
3. Check `http://localhost:8000/health` (works without API key)
4. Check `http://localhost:8000/version` (works without API key)

## API Endpoints

### GET `/health`
Returns service health status. Works without API key.

### GET `/version`
Returns service version and model metadata. Works without API key.

### POST `/review`
Review a lead using Groq LLM with structured output.

API key is validated on first call to `/review`. If missing, returns typed error.

**Request (nested domain structure):**
```json
{
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
    "email": "maya.patel@northwindhealth.io",
    "linkedin_url": "https://www.linkedin.com/in/mayapatel"
  },
  "routing": {
    "owner": "outbound-pipeline",
    "source": "apollo",
    "segment": "healthcare-saas-midmarket"
  },
  "signals": {
    "recent_funding": true,
    "hiring_activity": ["revops-manager", "sales-development-rep"],
    "tech_stack": ["salesforce", "hubspot", "snowflake"],
    "notes": "Expanding outbound motion across provider and payer verticals."
  },
  "state": {
    "status": "queued",
    "created_at": "2026-05-12T08:14:00Z"
  }
}
```

**Success Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "lead_id": "lead_20260512_0142",
  "confidence": 88,
  "rationale": "Company shows operational scaling signals and active AI adoption. VP of RevOps role indicates process optimization focus.",
  "strategy": "Focus outreach on workflow automation and operational efficiency gains for scaling operations.",
  "suggested_email_open": "Noticed your team is investing heavily in RevOps automation initiatives...",
  "model": "llama-3.3-70b-versatile",
  "latency_ms": 842,
  "reviewed_at": "2026-05-12T18:33:22Z"
}
```

**Error Response (missing API key):**
```json
{
  "status": "failed",
  "reason": "missing_api_key",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": "GROQ_API_KEY environment variable not set",
  "error_type": "missing_api_key"
}
```

## Implementation Details

### API Key Validation Timing

- ✓ Service boots cleanly even without `GROQ_API_KEY`
- ✓ `/health` and `/version` work without API key
- ✗ First `/review` call will fail with `missing_api_key` if key not set
- Validation happens on first inference call, not during import or startup

### Response Parsing & Validation

Model responses are:
1. Parsed from JSON (validates well-formed JSON)
2. Validated for all required fields
3. Type-checked (confidence is integer)
4. Range-checked (confidence 0-100)
5. Rejected if any validation fails (treated as operational error)

### Logging

Structured logs include:
- `request_id` for tracing
- `lead_id` for correlation
- `error_type` for operational categorization
- `latency_ms` for performance monitoring
- `model_name` for model tracking
- `inference_attempt` counter

## Current Scope

- ✓ Nested domain architecture (CompanyInfo, ContactInfo, RoutingInfo, SignalInfo, LeadState)
- ✓ Apollo-compatible payload structure
- ✓ Groq integration with strict JSON validation
- ✓ Schema validation with Pydantic
- ✓ Structured error responses with typed error codes
- ✓ Request-aware logging with operational context
- ✓ API key validation on first inference call
- ✓ Deterministic response contracts

## Not Yet Implemented

- Airtable integration
- HubSpot integration
- n8n workflows
- Redis queue logic
- Scoring engine
- Retries and deduplication
- Slack notifications
- Structured outputs via Groq response_format/json_schema mode (architecture prepared)

