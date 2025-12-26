"""
Pydantic models for explanation data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ExplainRequest(BaseModel):
    """User's explanation request."""
    
    video_id: str = Field(..., min_length=11, max_length=11)
    timestamp: float = Field(..., ge=0, description="Pause position in seconds")
    user_query: Optional[str] = Field(
        None, 
        description="Custom question or 'I didn't understand this'"
    )
    include_audio: bool = Field(True, description="Generate TTS?")
    
    # Context preferences
    context_window: int = Field(60, description="±seconds around timestamp")
    max_chunks: int = Field(8, description="Max chunks to retrieve")


class ExplanationChunk(BaseModel):
    """Retrieved chunk for context."""
    
    chunk_id: str
    text: str
    start_time: float
    end_time: float
    relevance_type: str  # "temporal", "foundational", "semantic"
    similarity_score: Optional[float] = None
    key_terms: List[str] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    """AI tutor explanation response."""
    
    # Text explanation
    explanation: str = Field(..., description="Structured markdown explanation")
    summary: str = Field(..., description="2-3 sentence TL;DR")
    
    # Audio (optional)
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    audio_duration: Optional[float] = Field(None, description="Audio length in seconds")
    
    # Context used
    retrieved_chunks: List[ExplanationChunk] = Field(default_factory=list)
    primary_topic: str = Field("", description="Main concept being explained")
    
    # Metadata
    timestamp: float
    processing_time_ms: int


class StreamEvent(BaseModel):
    """SSE stream event."""
    type: str  # "token", "audio", "done", "error"
    content: Optional[str] = None
    url: Optional[str] = None
