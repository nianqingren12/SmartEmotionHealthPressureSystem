"""FastAPI application entry point — Micro-Expression Recognition Commercial Prototype v5.0."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import config
from backend.db import DB_TYPE, init_db
from backend.inference import get_cached_inference_engine
from backend.middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)

# --------------- Logging ---------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# --------------- App ---------------
app = FastAPI(
    title=config.app_title,
    description="集用户注册、实时识别、报告生成、会员订阅和商业化功能于一体的可运行原型。",
    version=config.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --------------- Middleware (order matters: last added runs first) ---------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# --------------- Static files ---------------
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


# --------------- Exception handlers ---------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error_code": "INTERNAL_ERROR",
            "details": str(exc) if config.debug else None,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "details": None,
        },
    )


# --------------- Routers ---------------
from backend.routers.auth import router as auth_router
from backend.routers.recognition import router as recognition_router
from backend.routers.membership import router as membership_router
from backend.routers.admin import router as admin_router
from backend.routers.health import router as health_router
from backend.routers.assessment import router as assessment_router
from backend.routers.analytics import router as analytics_router

app.include_router(auth_router)
app.include_router(recognition_router)
app.include_router(membership_router)
app.include_router(admin_router)
app.include_router(health_router)
app.include_router(assessment_router)
app.include_router(analytics_router)


# --------------- Startup ---------------
@app.on_event("startup")
def startup_event() -> None:
    logger.info("Initializing database...")
    init_db()
    logger.info("Warming up inference engine...")
    get_cached_inference_engine()
    logger.info("Application startup complete. DB: %s, CORS: %s", DB_TYPE, config.cors_origins)


# --------------- System endpoints ---------------
@app.get("/api/system/status")
def get_system_status() -> dict[str, Any]:
    try:
        engine = get_cached_inference_engine()
        return {
            "inference_engine": {
                "name": engine.name,
                "version": getattr(engine, "version", "unknown"),
                "model_loaded": getattr(engine, "model_loaded", False)
                if hasattr(engine, "model_loaded")
                else False,
                "is_real_model": getattr(engine, "name", "").endswith("-Real"),
            },
            "database": {"type": DB_TYPE, "initialized": True},
            "version": config.app_version,
        }
    except Exception as e:
        logger.error("System status check failed: %s", e)
        return {
            "inference_engine": {
                "name": "unknown",
                "version": "unknown",
                "model_loaded": False,
                "is_real_model": False,
                "error": str(e),
            },
            "database": {"type": DB_TYPE, "initialized": True},
            "version": config.app_version,
        }


@app.get("/api/system/health")
def system_health() -> dict[str, Any]:
    from backend.inference import get_inference_engine
    from backend.db import utc_now

    engine = get_inference_engine()
    return {
        "status": "operational",
        "engine": engine.name,
        "version": engine.version,
        "model_loaded": engine.name != "DemoEngine",
        "db_type": DB_TYPE,
        "server_time": utc_now(),
    }


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
