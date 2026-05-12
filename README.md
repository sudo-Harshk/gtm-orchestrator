# gtm-orchestrator

An internal GTM workflow orchestration platform for healthcare SaaS outbound operations. Phase 1 establishes a reproducible infrastructure foundation for future workflow orchestration, AI-assisted processing, and operational integrations.

## Architecture

- FastAPI worker for local and containerized API execution
- Redis queue for future asynchronous orchestration
- Docker Compose for reproducible local startup
- Structured logging with request context support

## Quick Start

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Check `http://localhost:8000/health` and `http://localhost:8000/version`.

## Current Phase

Phase 1: Foundation Setup complete.

This phase is infrastructure-only. Business logic, AI inference, Airtable, HubSpot, n8n workflows, scoring, and workflow automation are intentionally deferred.
