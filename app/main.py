from __future__ import annotations

import os
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from app import __version__
from app.logger import configure_logging, get_logger, reset_request_id, set_request_id

load_dotenv()

configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

app = FastAPI(title="gtm-orchestrator", version=__version__)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    token = set_request_id(request_id)
    try:
        response: Response = await call_next(request)
    finally:
        reset_request_id(token)

    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "gtm-worker",
        "version": __version__,
        "model": "llama-3.3-70b",
        "environment": os.getenv("APP_ENV", "local"),
    }
