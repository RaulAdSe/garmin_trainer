"""FastAPI application for the Reactive Training App."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.routes import garmin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    print(f"Starting Reactive Training App v0.1.0")
    print(f"API running on {settings.api_host}:{settings.api_port}")
    yield
    # Shutdown
    print("Shutting down Reactive Training App")


app = FastAPI(
    title="Reactive Training API",
    description="AI-powered reactive training with Garmin Connect integration",
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

# Include routers
app.include_router(garmin.router, prefix="/api/v1/garmin", tags=["garmin"])


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


def run():
    """Run the application."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "reactive_training.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
