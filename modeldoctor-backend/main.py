"""ModelDoctor Backend — FastAPI Application Entry Point.

Features:
  - Structured logging (ISO timestamps + level + module)
  - Request timing middleware
  - Global exception handler
  - CORS configured for development
"""

from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from routers.diagnose import router as diagnose_router

load_dotenv()

# ──────────────────────────── Logging ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy third-party loggers
for noisy in ("httpcore", "httpx", "urllib3", "google", "grpc"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("modeldoctor")

# ──────────────────────────── App ────────────────────────────

app = FastAPI(
    title="ModelDoctor API",
    description="The MRI for your ML pipeline. AI-powered diagnostic system for silent ML failures.",
    version="2.0.0",
)

# CORS — allow frontend to communicate from any local port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").strip().lower() in ("1", "true", "yes"),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────── Request Timing Middleware ───────────────────
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Log every request with its response time."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.0f}"
    return response


# ──────────────────── Global Exception Handler ───────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean JSON error."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. The ModelDoctor team has been notified.",
            "error_type": type(exc).__name__,
        },
    )


# Mount routes
app.include_router(diagnose_router, prefix="/api", tags=["Diagnosis"])


@app.get("/")
async def root():
    return {
        "name": "ModelDoctor API",
        "version": "2.0.0",
        "tagline": "The MRI for your ML pipeline.",
        "team": "ASTROID — Prabhas N & Poornima Bhat",
        "architecture": "3-Layer Pipeline: Pattern Scanner → Data Analyzer → Gemini LLM",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
