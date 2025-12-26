"""
Application configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys - Must be set via environment variables
    OPENAI_API_KEY: str = ""  # Required: set via .env or environment
    ELEVENLABS_API_KEY: str = ""  # Optional: for TTS
    ANTHROPIC_API_KEY: str = ""  # Optional: for Claude LLM
    
    # Vector Store
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    
    # Audio Storage
    AUDIO_STORAGE_DIR: str = "./data/audio"
    
    # Cache
    REDIS_URL: str = ""
    
    # Providers
    TTS_PROVIDER: Literal["elevenlabs", "openai", "edge"] = "openai"
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # RAG Configuration
    CHUNK_TARGET_DURATION: float = 30.0
    CHUNK_MIN_DURATION: float = 20.0
    CHUNK_MAX_DURATION: float = 40.0
    CHUNK_OVERLAP_DURATION: float = 5.0
    
    RETRIEVAL_TEMPORAL_WINDOW: float = 60.0
    RETRIEVAL_MAX_CHUNKS: int = 8
    RETRIEVAL_MAX_PER_STRATEGY: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
