"""
Pydantic models for transcript data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TranscriptChunk(BaseModel):
    """Individual chunk of transcript with metadata."""
    
    # Identifiers
    chunk_id: str = Field(..., description="UUID: {video_id}_{start_time}_{seq}")
    video_id: str = Field(..., description="YouTube video ID (11 chars)")
    sequence: int = Field(..., description="Order within video (0, 1, 2, ...)")
    
    # Temporal boundaries
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    duration: float = Field(..., description="Chunk duration (20-40s target)")
    
    # Content
    text: str = Field(..., description="Raw transcript text")
    text_cleaned: str = Field("", description="Normalized text for embedding")
    
    # Semantic metadata
    key_terms: List[str] = Field(default_factory=list, description="Extracted technical terms")
    topic_label: Optional[str] = Field(None, description="Topic classification")
    is_foundational: bool = Field(False, description="Defines key concepts?")
    
    # Embedding
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "dQw4w9WgXcQ_65.5_3",
                "video_id": "dQw4w9WgXcQ",
                "sequence": 3,
                "start_time": 65.5,
                "end_time": 92.3,
                "duration": 26.8,
                "text": "Now let's talk about neural networks...",
                "text_cleaned": "neural networks brain artificial neurons",
                "key_terms": ["neural network", "neurons"],
                "is_foundational": True,
            }
        }


class RawSegment(BaseModel):
    """Raw transcript segment from YouTube."""
    text: str
    start: float
    duration: float
    
    @property
    def end(self) -> float:
        return self.start + self.duration


class VideoTranscript(BaseModel):
    """Complete video transcript with all chunks."""
    
    video_id: str
    title: str = ""
    channel: str = ""
    duration: float = 0.0  # Total video duration in seconds
    language: str = "en"   # Primary language (ISO 639-1)
    
    segments: List[RawSegment] = Field(default_factory=list)
    chunks: List[TranscriptChunk] = Field(default_factory=list)
    total_chunks: int = 0
    
    # Processing status
    status: str = "pending"  # "pending", "processing", "ready", "error"
    error_message: Optional[str] = None
    ingested_at: Optional[datetime] = None
    
    # Metadata
    source: str = "youtube_api"  # "youtube_api", "yt_dlp", "manual"


class IngestRequest(BaseModel):
    """Request to ingest a YouTube video."""
    video_id: str = Field(..., min_length=11, max_length=11)
    force_refresh: bool = False


class IngestResponse(BaseModel):
    """Response from ingestion request."""
    status: str  # "queued", "exists", "processing", "ready", "error"
    video_id: str
    message: str
    total_chunks: Optional[int] = None


class VideoStatusResponse(BaseModel):
    """Video ingestion status."""
    video_id: str
    status: str
    total_chunks: Optional[int] = None
    title: Optional[str] = None
    duration: Optional[float] = None
