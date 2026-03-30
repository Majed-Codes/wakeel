"""
Wakeel AI — FastAPI Application Entry Point.

Bachmann: "The main.py should be clean. Import, configure, mount routes.
No business logic here. This is the building lobby, not the workspace."
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import auth, transactions, chat, compliance, dashboard
from app.routes import forecast, upload, anomalies, alerts, reports, whatsapp
from app.routes import budget, zakat, vendors, payroll, advisor
# Ensure new model tables are created
from app.models import budget as _bm, vendor as _vm, employee as _em  # noqa: F401

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("wakeel")

# ── Create Tables ─────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(
    title="Wakeel AI — وكيل الذكي",
    description=(
        "المساعد المالي الذكي للمنشآت الصغيرة والمتوسطة في السعودية. "
        "Voice-first financial assistant for Saudi SMEs."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routes ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(chat.router)
app.include_router(compliance.router)
app.include_router(dashboard.router)
app.include_router(forecast.router)
app.include_router(upload.router)
app.include_router(anomalies.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(whatsapp.router)
app.include_router(budget.router)
app.include_router(zakat.router)
app.include_router(vendors.router)
app.include_router(payroll.router)
app.include_router(advisor.router)


# ── Root Health Check ─────────────────────────────────────────
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "anthropic_configured": settings.has_anthropic_key,
        "google_cloud_configured": settings.has_google_cloud,
        "openai_configured": settings.has_openai_key,
    }


@app.get("/api/v1/health", tags=["Health"])
async def api_health():
    # Determine LLM status
    if settings.has_anthropic_key:
        llm_status = "configured (Anthropic Claude)"
    elif settings.has_openai_key:
        llm_status = "configured (OpenAI fallback)"
    else:
        llm_status = "not_configured (mock mode)"

    # Determine transcription status
    if settings.has_google_cloud:
        stt_status = "configured (Google Cloud Speech)"
    elif settings.has_openai_key:
        stt_status = "configured (OpenAI Whisper fallback)"
    else:
        stt_status = "not_configured (mock mode)"

    return {
        "status": "ok",
        "services": {
            "database": "connected",
            "llm": llm_status,
            "transcription": stt_status,
            "openai": "configured" if settings.has_openai_key else "not_configured",
        },
    }


# ── Startup Event ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Wakeel AI backend starting...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Database: {settings.DATABASE_URL[:30]}...")
    logger.info(f"   LLM: {'✅ Anthropic Claude' if settings.has_anthropic_key else ('⚠️  OpenAI fallback' if settings.has_openai_key else '❌ mock mode')}")
    logger.info(f"   STT: {'✅ Google Cloud Speech' if settings.has_google_cloud else ('✅ Groq Whisper large-v3 (free)' if settings.has_groq_key else ('⚠️  OpenAI Whisper fallback' if settings.has_openai_key else '❌ mock mode'))}")
    logger.info("   API docs: http://localhost:8000/docs")
    logger.info("━" * 50)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.is_development,
    )
