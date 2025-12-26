"""
Health check endpoint.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "youtube-learning-assistant",
        "version": "1.0.0",
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "YouTube Learning Assistant API",
        "docs": "/docs",
    }
