"""FastAPI application for the Reactive Training App."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.routes import athlete, analysis, plans, workouts, export
from .api.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    print(f"Starting Reactive Training App v0.1.0")
    print(f"Training DB: {settings.training_db_path}")
    print(f"Wellness DB: {settings.wellness_db_path}")
    yield
    # Shutdown
    print("Shutting down Reactive Training App")


app = FastAPI(
    title="Reactive Training API",
    description="AI-powered training analysis and planning",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(athlete.router, prefix="/api/v1/athlete", tags=["athlete"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(plans.router, prefix="/api/v1/plans", tags=["plans"])
app.include_router(workouts.router, prefix="/api/v1/workouts", tags=["workouts"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Reactive Training API",
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
