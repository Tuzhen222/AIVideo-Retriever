from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.logger.logger import setup_logging, app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    setup_logging()
    app_logger.info("🚀 Starting FastAPI application...")
    app_logger.info(f"Log directory: logs/")
    app_logger.info(f"Search queries log: logs/search_queries.log")
    yield
    # Shutdown
    app_logger.info("🛑 Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description="API for video retrieval and search",
    version=settings.API_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "running",
        "debug": settings.DEBUG
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Video Retriever API"
    }


# Include routers
from app.api import search

app.include_router(search.router, prefix="/api", tags=["search"])

# Mount static files for keyframes
# Serve keyframes at /keyframes/... path
keyframe_dir = settings.KEYFRAME_DIR
if not os.path.isabs(keyframe_dir):
    # Make path absolute relative to app directory
    app_dir = os.path.dirname(os.path.dirname(__file__))
    keyframe_dir = os.path.join(app_dir, keyframe_dir)

if os.path.exists(keyframe_dir):
    app.mount("/keyframes", StaticFiles(directory=keyframe_dir), name="keyframes")
    app_logger.info(f"Mounted keyframe directory at /keyframes: {keyframe_dir}")
else:
    app_logger.warning(f"Keyframe directory not found: {keyframe_dir}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info"
    )

