"""FastAPI application for trAIner."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .api.routes import athlete, analysis, plans, workouts, export, garmin, chat, explain, gamification, strava, garmin_credentials, usage, stripe_webhook, admin, auth, safety, mileage_cap, preferences, pace_zones, manual_workouts, emotional
from .api.exception_handlers import register_exception_handlers
from .api.middleware.rate_limit import limiter
from .api.middleware.security_headers import SecurityHeadersMiddleware
from .db.database import TrainingDatabase
from .services.garmin_scheduler import get_scheduler, shutdown_scheduler
from .services.cleanup_scheduler import get_cleanup_scheduler, shutdown_cleanup_scheduler
from .utils.log_sanitizer import install_log_sanitizer

# Install log sanitization filter to prevent credential/PII leakage
# This must be done before any logging occurs
install_log_sanitizer()

# Configure logging
logger = logging.getLogger(__name__)


def validate_security_keys(settings) -> None:
    """Validate critical security keys at startup.

    Raises:
        SystemExit: If critical security keys are missing or invalid.
    """
    # JWT_SECRET_KEY - already validated by pydantic, but log confirmation
    # The config validator ensures it's at least 32 chars and not the default insecure value
    logger.info("JWT_SECRET_KEY: configured and validated")

    # CREDENTIAL_ENCRYPTION_KEY - critical if garmin_sync_enabled
    if settings.garmin_sync_enabled:
        if not settings.credential_encryption_key:
            logger.critical(
                "CREDENTIAL_ENCRYPTION_KEY is required when garmin_sync_enabled=true. "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            raise SystemExit(1)

        # Validate it's a valid Fernet key (44 chars, base64-encoded 32-byte key)
        if len(settings.credential_encryption_key) != 44:
            logger.critical(
                f"CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key (44 characters, got {len(settings.credential_encryption_key)}). "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            raise SystemExit(1)

        # Try to initialize Fernet to validate the key format
        try:
            from cryptography.fernet import Fernet
            Fernet(settings.credential_encryption_key.encode())
            logger.info("CREDENTIAL_ENCRYPTION_KEY: configured and validated")
        except Exception as e:
            logger.critical(
                f"CREDENTIAL_ENCRYPTION_KEY is not a valid Fernet key: {e}. "
                "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            raise SystemExit(1)
    else:
        if settings.credential_encryption_key:
            logger.info("CREDENTIAL_ENCRYPTION_KEY: configured (garmin_sync disabled)")
        else:
            logger.debug("CREDENTIAL_ENCRYPTION_KEY: not configured (garmin_sync disabled)")

    # OPENAI_API_KEY - warn if missing (LLM features won't work)
    if not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is not configured. LLM-powered features (chat, analysis, explanations) will not work."
        )
    else:
        logger.info("OPENAI_API_KEY: configured")

    # Optional keys - informational warnings
    if not settings.strava_client_id or not settings.strava_client_secret:
        logger.warning("Strava OAuth not configured. Strava integration will be unavailable.")
    else:
        logger.info("Strava OAuth: configured")

    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        logger.warning("Stripe not fully configured. Payment features will be unavailable.")
    else:
        logger.info("Stripe: configured")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    logger.info("Starting trAIner v0.1.0")
    logger.info(f"Training DB: {settings.training_db_path}")
    logger.info(f"Wellness DB: {settings.wellness_db_path}")

    # Validate security keys (fail fast if critical keys missing)
    logger.info("Validating security configuration...")
    validate_security_keys(settings)

    # Initialize database for schedulers
    training_db = TrainingDatabase(str(settings.training_db_path))

    # Initialize Garmin sync scheduler
    if settings.garmin_sync_enabled:
        try:
            scheduler = get_scheduler(training_db)
            scheduler.start(run_startup_sync=False)
            logger.info(f"Garmin sync scheduler started (daily sync at {settings.garmin_sync_hour}:00 UTC)")
        except Exception as e:
            logger.warning(f"Failed to start Garmin sync scheduler: {e}")
    else:
        logger.info("Garmin auto-sync is disabled")

    # Initialize data retention cleanup scheduler
    if settings.retention_cleanup_enabled:
        try:
            cleanup_scheduler = get_cleanup_scheduler(training_db)
            cleanup_scheduler.start()
            logger.info(f"Cleanup scheduler started (daily cleanup at {settings.retention_cleanup_hour}:00 UTC)")
        except Exception as e:
            logger.warning(f"Failed to start cleanup scheduler: {e}")
    else:
        logger.info("Data retention cleanup is disabled")

    yield

    # Shutdown
    logger.info("Shutting down trAIner")
    shutdown_scheduler()
    shutdown_cleanup_scheduler()


app = FastAPI(
    title="trAIner API",
    description="AI-powered training analysis and planning",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent 307 redirects that break auth through proxies
)

# Rate limiting
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded exceptions."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", None),
        },
    )


# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Security headers middleware
# Note: Middleware is added in reverse order (last added = first executed)
# Security headers should be added to all responses, so it goes after CORS
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=settings.security_csp,
    enable_hsts=settings.security_enable_hsts,
    hsts_max_age=settings.security_hsts_max_age,
    hsts_include_subdomains=settings.security_hsts_include_subdomains,
    hsts_preload=settings.security_hsts_preload,
)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(athlete.router, prefix="/api/v1/athlete", tags=["athlete"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(plans.router, prefix="/api/v1/plans", tags=["plans"])
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["workouts"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(garmin.router, prefix="/api/v1/garmin", tags=["garmin"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(explain.router, prefix="/api/v1/explain", tags=["explain"])
app.include_router(gamification.router, prefix="/api/v1/gamification", tags=["gamification"])
app.include_router(strava.router, prefix="/api/v1/strava", tags=["strava"])
app.include_router(garmin_credentials.router, prefix="/api/v1/garmin", tags=["garmin-credentials"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
app.include_router(stripe_webhook.router, prefix="/api/v1", tags=["stripe"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(safety.router, prefix="/api/v1/safety", tags=["safety"])
app.include_router(mileage_cap.router, prefix="/api/v1/athlete/mileage-cap", tags=["mileage-cap"])
app.include_router(preferences.router, prefix="/api/v1", tags=["preferences"])
app.include_router(pace_zones.router, prefix="/api/v1/pace-zones", tags=["pace-zones"])
app.include_router(manual_workouts.router, prefix="/api/v1/workouts/manual", tags=["manual-workouts"])
app.include_router(emotional.router, prefix="/api/v1/emotional", tags=["emotional"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "trAIner API",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
