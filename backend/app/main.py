from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.db import get_session_factory
from app.logging_policy import configure_logging, get_logger
from app.rate_limit import limiter
from app.routers import api_router
from app.services.audio_store import cleanup_expired_audio

logger = get_logger()
scheduler = BackgroundScheduler()


def _run_audio_cleanup() -> None:
    db = get_session_factory()()
    try:
        cleanup_expired_audio(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.environment != "test":
        scheduler.add_job(_run_audio_cleanup, "interval", hours=6, id="audio-cleanup", replace_existing=True)
        scheduler.start()
    logger.info("app_started", environment=settings.environment)
    yield
    if settings.environment != "test" and scheduler.running:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Hustle", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    if settings.environment == "test":
        limiter.enabled = False
    app.add_exception_handler(RateLimitExceeded, _rate_limited)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_and_access_log(request: Request, call_next) -> Response:
        started = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        logger.info(
            "http_request",
            http_method=request.method,
            http_path=request.url.path,
            status_code=response.status_code,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        return response

    app.include_router(api_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Too many requests"})


app = create_app()
