"""
YouTube Learning Assistant - FastAPI Backend
Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from config.settings import settings


# Create data directories early
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_STORAGE_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting YouTube Learning Assistant...")
    print(f"   📁 ChromaDB: {settings.CHROMA_PERSIST_DIR}")
    print(f"   🔊 Audio: {settings.AUDIO_STORAGE_DIR}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="YouTube Learning Assistant",
    description="AI-powered YouTube tutor with RAG-based explanations",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "chrome-extension://*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for audio (directory must exist)
try:
    app.mount("/api/audio", StaticFiles(directory=settings.AUDIO_STORAGE_DIR), name="audio")
except Exception as e:
    print(f"⚠️ Could not mount audio directory: {e}")

# Register routes
from api.routes import health, transcript, explain

app.include_router(health.router)
app.include_router(transcript.router)
app.include_router(explain.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
