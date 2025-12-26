# YouTube Learning Assistant - System Architecture

## Overview

A YouTube Learning Assistant that extracts video transcripts, builds a RAG-based knowledge system, and provides contextual AI tutoring with text and audio explanations.

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BROWSER EXTENSION                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ Video State │  │ Pause        │  │ Timestamp   │  │ Extension       │   │
│  │ Monitor     │  │ Detection    │  │ Extractor   │  │ Popup UI        │   │
│  └─────────────┘  └──────────────┘  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ WebSocket / REST
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NEXT.JS FRONTEND                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ Video       │  │ Explanation  │  │ Audio       │  │ Learning        │   │
│  │ Dashboard   │  │ Panel        │  │ Player      │  │ History         │   │
│  └─────────────┘  └──────────────┘  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ REST API + SSE Streaming
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PYTHON BACKEND (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API GATEWAY / ROUTER                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌───────────────┬──────────────────┼──────────────────┬───────────────┐   │
│  ▼               ▼                  ▼                  ▼               ▼   │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐ ┌───────────┐ ┌─────────┐   │
│  │Transcript │ │Ingestion  │ │RAG Retrieval  │ │LLM Tutor  │ │TTS      │   │
│  │Extractor  │ │Pipeline   │ │Engine         │ │Service    │ │Service  │   │
│  └───────────┘ └───────────┘ └───────────────┘ └───────────┘ └─────────┘   │
│        │              │              │               │             │        │
└────────┼──────────────┼──────────────┼───────────────┼─────────────┼────────┘
         │              │              │               │             │
         ▼              ▼              ▼               ▼             ▼
┌─────────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│ YouTube API │  │ ChromaDB  │  │ ChromaDB  │  │ OpenAI/   │  │ ElevenLabs│
│ / yt-dlp    │  │ / FAISS   │  │ / FAISS   │  │ Claude    │  │ / OpenAI  │
└─────────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

---

## 2. Component Breakdown

### 2.1 Browser Extension (Chrome/Firefox)
**Purpose:** Detect video state, extract timestamps, trigger explanations

```
extension/
├── manifest.json           # Extension config (Manifest V3)
├── content/
│   ├── youtube-observer.js # Monitors video player state
│   └── timestamp-tracker.js
├── popup/
│   ├── popup.html          # Extension popup UI
│   └── popup.js
├── background/
│   └── service-worker.js   # Background communication
└── styles/
    └── popup.css
```

**Key Responsibilities:**
- Detect video pause events
- Extract current timestamp (seconds)
- Extract video ID from URL
- Send "explain this" requests to backend
- Display inline explanations or open web app

### 2.2 Next.js Frontend
**Purpose:** Main web application for viewing explanations, history, settings

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Landing page
│   ├── video/[videoId]/page.tsx    # Video-specific learning view
│   ├── history/page.tsx            # Learning history
│   └── api/                        # API routes (BFF pattern)
│       └── proxy/[...path]/route.ts
├── components/
│   ├── video/
│   │   ├── VideoPlayer.tsx         # Embedded YouTube player
│   │   ├── TranscriptView.tsx      # Side panel transcript
│   │   └── TimestampMarker.tsx
│   ├── explanation/
│   │   ├── ExplanationCard.tsx     # Text explanation display
│   │   ├── AudioPlayer.tsx         # TTS playback
│   │   └── LoadingState.tsx
│   └── common/
│       ├── Header.tsx
│       └── Footer.tsx
├── lib/
│   ├── api.ts                      # Backend API client
│   └── youtube.ts                  # YouTube utils
└── types/
    └── index.ts                    # TypeScript types
```

### 2.3 Python Backend (FastAPI)
**Purpose:** Core AI pipeline, RAG, LLM orchestration, TTS

```
backend/
├── main.py                         # FastAPI app entry
├── config/
│   └── settings.py                 # Environment config
├── api/
│   ├── routes/
│   │   ├── transcript.py           # POST /transcript/ingest
│   │   ├── explain.py              # POST /explain
│   │   └── health.py               # GET /health
│   └── dependencies.py
├── services/
│   ├── transcript/
│   │   ├── extractor.py            # YouTube transcript extraction
│   │   └── chunker.py              # Semantic chunking logic
│   ├── rag/
│   │   ├── embeddings.py           # Embedding generation
│   │   ├── vector_store.py         # ChromaDB/FAISS operations
│   │   └── retriever.py            # Multi-strategy retrieval
│   ├── llm/
│   │   ├── tutor.py                # LLM prompt + response
│   │   └── prompts.py              # Prompt templates
│   └── tts/
│       └── synthesizer.py          # Text-to-speech
├── models/
│   ├── transcript.py               # Pydantic models
│   └── explanation.py
└── utils/
    ├── cache.py                    # Redis cache utilities
    └── timing.py                   # Latency tracking
```

---

## 3. Data Structures

### 3.1 Transcript Chunk Schema

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TranscriptChunk(BaseModel):
    """Individual chunk of transcript with metadata"""
    
    # Identifiers
    chunk_id: str                    # UUID: "{video_id}_{start_time}_{seq}"
    video_id: str                    # YouTube video ID (11 chars)
    sequence: int                    # Order within video (0, 1, 2, ...)
    
    # Temporal boundaries
    start_time: float                # Start timestamp in seconds
    end_time: float                  # End timestamp in seconds
    duration: float                  # Chunk duration (20-40s target)
    
    # Content
    text: str                        # Raw transcript text
    text_cleaned: str                # Normalized text for embedding
    
    # Semantic metadata
    key_terms: List[str]             # Extracted technical terms
    topic_label: Optional[str]       # Topic classification (optional)
    is_foundational: bool            # Defines key concepts?
    
    # Embedding
    embedding: Optional[List[float]] # 1536-dim vector (OpenAI) or 384-dim (sentence-transformers)
    
    # Timestamps
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "dQw4w9WgXcQ_65.5_3",
                "video_id": "dQw4w9WgXcQ",
                "sequence": 3,
                "start_time": 65.5,
                "end_time": 92.3,
                "duration": 26.8,
                "text": "Now let's talk about neural networks. A neural network is like a brain...",
                "text_cleaned": "neural networks brain artificial neurons layers",
                "key_terms": ["neural network", "neurons", "layers"],
                "topic_label": "neural_networks_intro",
                "is_foundational": True,
                "embedding": [0.023, -0.145, ...],
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class VideoTranscript(BaseModel):
    """Complete video transcript with all chunks"""
    
    video_id: str
    title: str
    channel: str
    duration: float                  # Total video duration in seconds
    language: str                    # Primary language (ISO 639-1)
    
    chunks: List[TranscriptChunk]
    total_chunks: int
    
    # Processing status
    status: str                      # "pending", "processing", "ready", "error"
    ingested_at: Optional[datetime]
    
    # Metadata
    source: str                      # "youtube_api", "yt_dlp", "manual"


class ChunkMetadata(BaseModel):
    """Lightweight metadata for vector store"""
    
    chunk_id: str
    video_id: str
    start_time: float
    end_time: float
    sequence: int
    is_foundational: bool
    key_terms: List[str]
```

### 3.2 Explanation Request/Response

```python
class ExplainRequest(BaseModel):
    """User's explanation request"""
    
    video_id: str
    timestamp: float                 # Pause position in seconds
    user_query: Optional[str]        # "I didn't understand this" or custom
    include_audio: bool = True       # Generate TTS?
    
    # Context preferences
    context_window: int = 60         # ±60 seconds around timestamp
    max_chunks: int = 8              # Max chunks to retrieve


class ExplanationChunk(BaseModel):
    """Retrieved chunk for context"""
    
    chunk_id: str
    text: str
    start_time: float
    end_time: float
    relevance_type: str              # "temporal", "foundational", "semantic"
    similarity_score: Optional[float]


class ExplainResponse(BaseModel):
    """AI tutor explanation response"""
    
    # Text explanation
    explanation: str                 # Structured markdown explanation
    summary: str                     # 2-3 sentence TL;DR
    
    # Audio (optional)
    audio_url: Optional[str]         # Signed URL to audio file
    audio_duration: Optional[float]  # Audio length in seconds
    
    # Context used
    retrieved_chunks: List[ExplanationChunk]
    primary_topic: str               # Main concept being explained
    
    # Metadata
    timestamp: float
    processing_time_ms: int
```

---

## 4. RAG Pipeline

### 4.1 Ingestion Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. Extract   │───▶│ 2. Clean &   │───▶│ 3. Chunk     │───▶│ 4. Embed    │
│ Transcript   │    │ Normalize    │    │ by Meaning   │    │ Chunks       │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                    │
                                                                    ▼
                                                            ┌──────────────┐
                                                            │ 5. Store in  │
                                                            │ Vector DB    │
                                                            └──────────────┘
```

```python
# services/transcript/chunker.py

from typing import List, Tuple
import re
from dataclasses import dataclass

@dataclass
class RawSegment:
    text: str
    start: float
    end: float

class SemanticChunker:
    """
    Chunks transcript by semantic meaning with timestamp awareness.
    Target: 20-40 second chunks with 5-second overlap.
    """
    
    def __init__(
        self,
        target_duration: float = 30.0,      # Target chunk duration
        min_duration: float = 20.0,
        max_duration: float = 40.0,
        overlap_duration: float = 5.0,       # Overlap for context continuity
    ):
        self.target_duration = target_duration
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.overlap_duration = overlap_duration
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]\s+')
        self.topic_markers = [
            "now let's", "next,", "moving on", "another", 
            "first,", "second,", "finally,", "in conclusion",
            "the next thing", "here's", "so basically"
        ]
    
    def chunk(self, segments: List[RawSegment]) -> List[TranscriptChunk]:
        """
        Main chunking algorithm:
        1. Merge tiny segments
        2. Split at natural boundaries
        3. Ensure duration constraints
        4. Add overlapping context
        """
        chunks = []
        current_text = ""
        current_start = 0.0
        current_end = 0.0
        
        for segment in segments:
            potential_end = segment.end
            potential_duration = potential_end - current_start
            
            # Check if we should split
            should_split = (
                potential_duration >= self.max_duration or
                (potential_duration >= self.min_duration and 
                 self._is_natural_boundary(segment.text))
            )
            
            if should_split and current_text:
                # Create chunk
                chunks.append(self._create_chunk(
                    text=current_text,
                    start=current_start,
                    end=current_end,
                    sequence=len(chunks)
                ))
                
                # Start new chunk with overlap
                overlap_start = max(current_start, current_end - self.overlap_duration)
                current_text = self._get_overlap_text(segments, overlap_start, current_end)
                current_start = overlap_start
            
            current_text += " " + segment.text
            current_end = segment.end
        
        # Don't forget last chunk
        if current_text.strip():
            chunks.append(self._create_chunk(
                text=current_text,
                start=current_start,
                end=current_end,
                sequence=len(chunks)
            ))
        
        return chunks
    
    def _is_natural_boundary(self, text: str) -> bool:
        """Check if text contains a natural topic transition"""
        text_lower = text.lower().strip()
        
        # Strong boundary: topic marker at start
        for marker in self.topic_markers:
            if text_lower.startswith(marker):
                return True
        
        # Medium boundary: ends with sentence
        if self.sentence_endings.search(text):
            return True
            
        return False
    
    def _create_chunk(self, text: str, start: float, end: float, sequence: int) -> TranscriptChunk:
        """Create a chunk with extracted metadata"""
        from services.rag.embeddings import extract_key_terms
        
        text = text.strip()
        key_terms = extract_key_terms(text)
        
        return TranscriptChunk(
            chunk_id=f"{self.video_id}_{start:.1f}_{sequence}",
            video_id=self.video_id,
            sequence=sequence,
            start_time=start,
            end_time=end,
            duration=end - start,
            text=text,
            text_cleaned=self._clean_for_embedding(text),
            key_terms=key_terms,
            is_foundational=self._is_foundational(text, key_terms),
            embedding=None,  # Set later
            created_at=datetime.utcnow()
        )
    
    def _is_foundational(self, text: str, key_terms: List[str]) -> bool:
        """Detect if chunk defines fundamental concepts"""
        definitional_patterns = [
            r'\b(\w+)\s+is\s+(a|an|the)\s+',
            r'\bwhat\s+is\s+',
            r'\bdefined\s+as\b',
            r'\bmeans\s+that\b',
            r'\brefers\s+to\b',
            r'\bbasically\b',
            r'\bin\s+simple\s+terms\b',
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in definitional_patterns)
```

### 4.2 Retrieval Pipeline

```python
# services/rag/retriever.py

from typing import List, Tuple
from enum import Enum

class RetrievalStrategy(Enum):
    TEMPORAL = "temporal"           # Chunks around timestamp
    FOUNDATIONAL = "foundational"   # Definition chunks
    SEMANTIC = "semantic"           # Similarity search


class MultiStrategyRetriever:
    """
    Three-pronged retrieval strategy:
    1. Temporal: ±60s around pause timestamp
    2. Foundational: Earlier chunks that define terms used at timestamp
    3. Semantic: Similar content from anywhere in video
    """
    
    def __init__(
        self,
        vector_store,
        embedding_model,
        temporal_window: float = 60.0,
        max_chunks_per_strategy: int = 3,
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.temporal_window = temporal_window
        self.max_per_strategy = max_chunks_per_strategy
    
    async def retrieve(
        self,
        video_id: str,
        timestamp: float,
        query: str = None,
        max_total_chunks: int = 8,
    ) -> List[ExplanationChunk]:
        """
        Execute multi-strategy retrieval and merge results.
        """
        
        results = []
        seen_chunk_ids = set()
        
        # ─────────────────────────────────────────────
        # Strategy 1: TEMPORAL (highest priority)
        # ─────────────────────────────────────────────
        temporal_chunks = await self._retrieve_temporal(
            video_id=video_id,
            timestamp=timestamp,
            window=self.temporal_window,
        )
        for chunk in temporal_chunks[:self.max_per_strategy]:
            if chunk.chunk_id not in seen_chunk_ids:
                chunk.relevance_type = "temporal"
                results.append(chunk)
                seen_chunk_ids.add(chunk.chunk_id)
        
        # ─────────────────────────────────────────────
        # Strategy 2: FOUNDATIONAL
        # Find earlier chunks that define terms used in temporal context
        # ─────────────────────────────────────────────
        if temporal_chunks:
            # Extract terms from temporal chunks
            temporal_terms = set()
            for chunk in temporal_chunks:
                temporal_terms.update(chunk.key_terms)
            
            foundational_chunks = await self._retrieve_foundational(
                video_id=video_id,
                terms=list(temporal_terms),
                before_timestamp=timestamp,
            )
            
            for chunk in foundational_chunks[:self.max_per_strategy]:
                if chunk.chunk_id not in seen_chunk_ids:
                    chunk.relevance_type = "foundational"
                    results.append(chunk)
                    seen_chunk_ids.add(chunk.chunk_id)
        
        # ─────────────────────────────────────────────
        # Strategy 3: SEMANTIC SIMILARITY
        # ─────────────────────────────────────────────
        # Build query from timestamp context + user query
        context_text = " ".join([c.text for c in temporal_chunks[:2]])
        search_query = f"{query or ''} {context_text}"
        
        semantic_chunks = await self._retrieve_semantic(
            video_id=video_id,
            query=search_query,
            exclude_ids=seen_chunk_ids,
        )
        
        remaining_slots = max_total_chunks - len(results)
        for chunk in semantic_chunks[:remaining_slots]:
            if chunk.chunk_id not in seen_chunk_ids:
                chunk.relevance_type = "semantic"
                results.append(chunk)
                seen_chunk_ids.add(chunk.chunk_id)
        
        # Sort by timestamp for coherent context
        results.sort(key=lambda x: x.start_time)
        
        return results[:max_total_chunks]
    
    async def _retrieve_temporal(
        self,
        video_id: str,
        timestamp: float,
        window: float,
    ) -> List[ExplanationChunk]:
        """
        Get chunks within ±window seconds of timestamp.
        Uses metadata filtering, not vector search.
        """
        return await self.vector_store.query_by_time_range(
            video_id=video_id,
            start=max(0, timestamp - window),
            end=timestamp + window,
            order_by_distance_to=timestamp,  # Closest first
        )
    
    async def _retrieve_foundational(
        self,
        video_id: str,
        terms: List[str],
        before_timestamp: float,
    ) -> List[ExplanationChunk]:
        """
        Find chunks that define the given terms.
        Only looks at chunks BEFORE the current timestamp.
        """
        return await self.vector_store.query_by_metadata(
            video_id=video_id,
            filters={
                "is_foundational": True,
                "end_time": {"$lt": before_timestamp},
                "key_terms": {"$in": terms},
            },
            order_by="sequence",  # Earlier definitions first
        )
    
    async def _retrieve_semantic(
        self,
        video_id: str,
        query: str,
        exclude_ids: set,
    ) -> List[ExplanationChunk]:
        """
        Vector similarity search across entire transcript.
        """
        query_embedding = await self.embedding_model.embed(query)
        
        results = await self.vector_store.similarity_search(
            video_id=video_id,
            query_embedding=query_embedding,
            top_k=self.max_per_strategy * 2,  # Extra for filtering
        )
        
        # Filter out already-retrieved chunks
        return [r for r in results if r.chunk_id not in exclude_ids]
```

### 4.3 Vector Store Implementation

```python
# services/rag/vector_store.py

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

class ChromaVectorStore:
    """
    ChromaDB-based vector store with metadata filtering.
    
    Why ChromaDB:
    - Runs locally (no external service needed)
    - Built-in metadata filtering
    - Good for prototyping (can migrate to Pinecone later)
    - Persistent storage option
    """
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection(
            name="youtube_transcripts",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def upsert_chunks(self, chunks: List[TranscriptChunk]) -> None:
        """Store chunks with embeddings and metadata"""
        
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            metadatas=[{
                "video_id": c.video_id,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "sequence": c.sequence,
                "is_foundational": c.is_foundational,
                "key_terms": ",".join(c.key_terms),  # ChromaDB needs strings
            } for c in chunks],
            documents=[c.text for c in chunks],
        )
    
    async def query_by_time_range(
        self,
        video_id: str,
        start: float,
        end: float,
        order_by_distance_to: float = None,
    ) -> List[ExplanationChunk]:
        """Retrieve chunks within time range"""
        
        results = self.collection.get(
            where={
                "$and": [
                    {"video_id": {"$eq": video_id}},
                    {"start_time": {"$gte": start}},
                    {"end_time": {"$lte": end}},
                ]
            },
            include=["documents", "metadatas"]
        )
        
        chunks = self._results_to_chunks(results)
        
        if order_by_distance_to is not None:
            chunks.sort(
                key=lambda c: abs(c.start_time - order_by_distance_to)
            )
        
        return chunks
    
    async def similarity_search(
        self,
        video_id: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[ExplanationChunk]:
        """Semantic similarity search"""
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where={"video_id": {"$eq": video_id}},
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        chunks = self._results_to_chunks(results)
        
        # Add similarity scores
        if results["distances"]:
            for i, chunk in enumerate(chunks):
                chunk.similarity_score = 1 - results["distances"][0][i]
        
        return chunks
```

---

## 5. Prompt Templates

```python
# services/llm/prompts.py

from typing import List
from models.explanation import ExplanationChunk

class TutorPrompts:
    """
    Prompt templates for the AI tutor.
    
    Design principles:
    1. ZERO prior knowledge assumption
    2. Define ALL technical terms
    3. Use analogies and real-world examples
    4. Follow video's teaching flow
    5. Never hallucinate beyond provided context
    """
    
    SYSTEM_PROMPT = """You are a patient, expert AI tutor helping a student understand a YouTube video.

## Your Teaching Style
- Assume the student has ZERO prior knowledge of this topic
- Define EVERY technical term before using it
- Use simple, conversational language (8th grade reading level)
- Give real-world analogies for abstract concepts
- Build understanding step-by-step

## Rules
1. ONLY explain concepts from the provided transcript context
2. If information isn't in the context, say "The video doesn't cover this, but..."
3. Follow the video's teaching order - don't jump ahead
4. Keep explanations focused on the timestamp the student paused at
5. Format explanations with clear structure (headers, bullets, analogies)

## Response Format
Always structure your response as:

### 🎯 What's Being Discussed
[1-2 sentence summary of the concept at this timestamp]

### 📖 Simple Explanation
[Clear explanation with definitions and analogies]

### 🔗 How It Connects
[How this relates to earlier concepts from the video]

### 💡 Key Takeaway
[One memorable sentence summarizing the main idea]
"""

    @staticmethod
    def build_explanation_prompt(
        chunks: List[ExplanationChunk],
        timestamp: float,
        user_query: str = None,
    ) -> str:
        """Build the user prompt with retrieved context"""
        
        # Separate chunks by type for clear context
        temporal = [c for c in chunks if c.relevance_type == "temporal"]
        foundational = [c for c in chunks if c.relevance_type == "foundational"]
        semantic = [c for c in chunks if c.relevance_type == "semantic"]
        
        prompt = f"""## Student's Question
The student paused the video at timestamp {TutorPrompts._format_time(timestamp)}.
{f'They asked: "{user_query}"' if user_query else 'They said: "I don\'t understand this"'}

## Video Transcript Context

### Currently Being Discussed (around {TutorPrompts._format_time(timestamp)})
"""
        for chunk in temporal:
            prompt += f"\n[{TutorPrompts._format_time(chunk.start_time)} - {TutorPrompts._format_time(chunk.end_time)}]\n{chunk.text}\n"
        
        if foundational:
            prompt += "\n### Earlier Definitions & Foundations\n"
            for chunk in foundational:
                prompt += f"\n[{TutorPrompts._format_time(chunk.start_time)}]\n{chunk.text}\n"
        
        if semantic:
            prompt += "\n### Related Concepts from This Video\n"
            for chunk in semantic:
                prompt += f"\n[{TutorPrompts._format_time(chunk.start_time)}]\n{chunk.text}\n"
        
        prompt += """
---
Now explain what's happening at this point in the video. Remember:
- Define all technical terms
- Use simple analogies
- Don't assume prior knowledge
- Only use information from the transcript above"""
        
        return prompt
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Convert seconds to MM:SS format"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    # For TTS: Generate speaking-friendly version
    AUDIO_SIMPLIFICATION_PROMPT = """Convert the following explanation into natural spoken text.

Rules:
- Remove all markdown formatting (headers, bullets, bold)
- Convert symbols like 🎯 to spoken equivalents or remove them
- Make it sound like a tutor speaking calmly and clearly
- Keep the same content and structure
- Use transitional phrases ("So,", "Now,", "The key thing here is...")
- Keep it under 60 seconds when spoken (roughly 150 words)

Original explanation:
{explanation}

Spoken version:"""
```

---

## 6. API Flow

### 6.1 Ingestion API

```python
# api/routes/transcript.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/transcript", tags=["transcript"])


class IngestRequest(BaseModel):
    video_id: str                    # YouTube video ID
    force_refresh: bool = False      # Re-ingest even if exists


class IngestResponse(BaseModel):
    status: str                      # "queued", "exists", "processing"
    video_id: str
    message: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_transcript(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    transcript_service: TranscriptService = Depends(),
    vector_store: ChromaVectorStore = Depends(),
):
    """
    Ingest a YouTube video transcript into the RAG system.
    
    Flow:
    1. Check if video already ingested (return early if so)
    2. Extract transcript from YouTube
    3. Chunk by semantic meaning
    4. Generate embeddings
    5. Store in vector database
    """
    
    # Check cache
    if not request.force_refresh:
        existing = await vector_store.video_exists(request.video_id)
        if existing:
            return IngestResponse(
                status="exists",
                video_id=request.video_id,
                message="Video already ingested"
            )
    
    # Queue background processing
    background_tasks.add_task(
        _process_ingestion,
        video_id=request.video_id,
        transcript_service=transcript_service,
        vector_store=vector_store,
    )
    
    return IngestResponse(
        status="queued",
        video_id=request.video_id,
        message="Ingestion started in background"
    )


async def _process_ingestion(
    video_id: str,
    transcript_service: TranscriptService,
    vector_store: ChromaVectorStore,
):
    """Background task for full ingestion pipeline"""
    
    # 1. Extract transcript
    raw_transcript = await transcript_service.extract(video_id)
    
    # 2. Chunk semantically
    chunker = SemanticChunker(video_id=video_id)
    chunks = chunker.chunk(raw_transcript.segments)
    
    # 3. Generate embeddings (batch for efficiency)
    embeddings = await embedding_service.embed_batch(
        [c.text_cleaned for c in chunks]
    )
    for chunk, emb in zip(chunks, embeddings):
        chunk.embedding = emb
    
    # 4. Store in vector database
    await vector_store.upsert_chunks(chunks)
    
    # 5. Update status
    await cache.set(f"video_status:{video_id}", "ready")
```

### 6.2 Explanation API

```python
# api/routes/explain.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter(prefix="/api/explain", tags=["explain"])


@router.post("/", response_model=ExplainResponse)
async def explain_timestamp(
    request: ExplainRequest,
    retriever: MultiStrategyRetriever = Depends(),
    llm_service: TutorLLM = Depends(),
    tts_service: TTSService = Depends(),
):
    """
    Generate AI explanation for a specific video timestamp.
    
    Flow:
    1. Retrieve relevant chunks (temporal + foundational + semantic)
    2. Build structured prompt with context
    3. Generate text explanation via LLM
    4. (Optional) Convert to audio via TTS
    5. Return combined response
    """
    
    start_time = time.time()
    
    # 1. Check video is ingested
    video_ready = await cache.get(f"video_status:{request.video_id}")
    if video_ready != "ready":
        raise HTTPException(
            status_code=400,
            detail="Video not yet ingested. Call /transcript/ingest first."
        )
    
    # 2. Retrieve relevant chunks
    chunks = await retriever.retrieve(
        video_id=request.video_id,
        timestamp=request.timestamp,
        query=request.user_query,
        max_total_chunks=request.max_chunks,
    )
    
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No transcript found for this timestamp"
        )
    
    # 3. Build prompt and generate explanation
    prompt = TutorPrompts.build_explanation_prompt(
        chunks=chunks,
        timestamp=request.timestamp,
        user_query=request.user_query,
    )
    
    explanation = await llm_service.generate(
        system_prompt=TutorPrompts.SYSTEM_PROMPT,
        user_prompt=prompt,
    )
    
    # 4. Generate audio if requested
    audio_url = None
    audio_duration = None
    
    if request.include_audio:
        # Simplify for speech
        spoken_text = await llm_service.generate(
            system_prompt="You are a text formatter.",
            user_prompt=TutorPrompts.AUDIO_SIMPLIFICATION_PROMPT.format(
                explanation=explanation
            ),
        )
        
        # Generate TTS
        audio_url, audio_duration = await tts_service.synthesize(
            text=spoken_text,
            video_id=request.video_id,
            timestamp=request.timestamp,
        )
    
    # 5. Extract summary
    summary = explanation.split("\n\n")[0][:200]  # First paragraph
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return ExplainResponse(
        explanation=explanation,
        summary=summary,
        audio_url=audio_url,
        audio_duration=audio_duration,
        retrieved_chunks=[
            ExplanationChunk(
                chunk_id=c.chunk_id,
                text=c.text[:200] + "...",  # Truncate for response
                start_time=c.start_time,
                end_time=c.end_time,
                relevance_type=c.relevance_type,
                similarity_score=c.similarity_score,
            ) for c in chunks
        ],
        primary_topic=chunks[0].key_terms[0] if chunks[0].key_terms else "General",
        timestamp=request.timestamp,
        processing_time_ms=processing_time,
    )


@router.post("/stream")
async def explain_timestamp_stream(request: ExplainRequest):
    """
    SSE streaming version for lower perceived latency.
    Streams explanation tokens as they're generated.
    """
    
    async def generate():
        # ... retrieval logic same as above ...
        
        async for token in llm_service.generate_stream(
            system_prompt=TutorPrompts.SYSTEM_PROMPT,
            user_prompt=prompt,
        ):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        
        # Send audio URL at the end
        if request.include_audio:
            # ... TTS logic ...
            yield f"data: {json.dumps({'type': 'audio', 'url': audio_url})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
```

### 6.3 TTS Service

```python
# services/tts/synthesizer.py

import aiohttp
from typing import Tuple, Optional
import os

class TTSService:
    """
    Text-to-Speech service using ElevenLabs or OpenAI TTS.
    
    Cost optimization:
    - Cache audio files by content hash
    - Use fastest model for real-time response
    - Stream audio when possible
    """
    
    def __init__(
        self,
        provider: str = "elevenlabs",  # or "openai"
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs "Rachel" - calm tutor voice
        storage_path: str = "./data/audio",
    ):
        self.provider = provider
        self.voice_id = voice_id
        self.storage_path = storage_path
        
        if provider == "elevenlabs":
            self.api_key = os.getenv("ELEVENLABS_API_KEY")
            self.api_url = "https://api.elevenlabs.io/v1/text-to-speech"
        else:
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.api_url = "https://api.openai.com/v1/audio/speech"
    
    async def synthesize(
        self,
        text: str,
        video_id: str,
        timestamp: float,
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Generate audio from text.
        Returns: (audio_url, duration_seconds)
        """
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        # Generate audio
        if self.provider == "elevenlabs":
            audio_bytes = await self._elevenlabs_tts(text)
        else:
            audio_bytes = await self._openai_tts(text)
        
        if not audio_bytes:
            return None, None
        
        # Save and get URL
        filename = f"{video_id}_{int(timestamp)}_{cache_key[:8]}.mp3"
        filepath = os.path.join(self.storage_path, filename)
        
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        
        # Calculate duration (rough estimate: ~150 words/minute)
        word_count = len(text.split())
        duration = (word_count / 150) * 60
        
        audio_url = f"/api/audio/{filename}"
        
        # Cache result
        await self._cache_audio(cache_key, audio_url, duration)
        
        return audio_url, duration
    
    async def _elevenlabs_tts(self, text: str) -> bytes:
        """ElevenLabs API call"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2",  # Fastest model
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,               # Natural, not dramatic
                        "use_speaker_boost": True,
                    },
                },
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None
    
    async def _openai_tts(self, text: str) -> bytes:
        """OpenAI TTS API call"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",           # Faster, lower quality
                    "voice": "nova",            # Calm, neutral voice
                    "input": text,
                    "response_format": "mp3",
                },
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None
```

---

## 7. Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Browser Extension  │  Next.js Frontend                   │    │
│  │ - Video detection  │  - UI components                    │    │
│  │ - Timestamp        │  - API calls                        │    │
│  │ - Popup UI         │  - State management                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ FastAPI Backend                                          │    │
│  │ ┌───────────┐  ┌───────────┐  ┌───────────┐            │    │
│  │ │ Routes    │  │ Services  │  │ Models    │            │    │
│  │ │ (API)     │  │ (Logic)   │  │ (Schemas) │            │    │
│  │ └───────────┘  └───────────┘  └───────────┘            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       INTELLIGENCE LAYER                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ RAG Pipeline  │  │ LLM Service   │  │ TTS Service       │   │
│  │ - Chunking    │  │ - Prompting   │  │ - Audio synthesis │   │
│  │ - Embedding   │  │ - Generation  │  │ - Caching         │   │
│  │ - Retrieval   │  │ - Streaming   │  │                   │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ Vector Store  │  │ Cache         │  │ File Storage      │   │
│  │ (ChromaDB)    │  │ (Redis)       │  │ (Audio files)     │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ YouTube API   │  │ OpenAI/Claude │  │ ElevenLabs        │   │
│  │ yt-dlp        │  │ Anthropic     │  │ OpenAI TTS        │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Responsibility Breakdown

| Layer | Component | Responsibilities |
|-------|-----------|------------------|
| **Presentation** | Extension | Detect pauses, extract timestamps, trigger requests |
| | Frontend | Display explanations, audio player, history |
| **Application** | Routes | HTTP handling, validation, response formatting |
| | Services | Business logic, orchestration |
| | Models | Data validation, serialization |
| **Intelligence** | RAG | Chunking, embedding, multi-strategy retrieval |
| | LLM | Prompt construction, generation, streaming |
| | TTS | Text-to-speech synthesis, voice selection |
| **Data** | Vector Store | Embedding storage, similarity search |
| | Cache | Response caching, status tracking |
| | File Storage | Audio file persistence |

---

## 8. Performance & Cost Optimization

### Latency Optimization

```
Target: < 3s for text, < 5s for text + audio

┌─────────────────────────────────────────────────────────────────┐
│ Optimization Strategies                                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. Pre-ingestion: Index videos when first opened                │
│ 2. Streaming: Stream LLM tokens as generated                    │
│ 3. Caching: Cache common explanations by (video_id, timestamp)  │
│ 4. Parallel: Generate text and audio in parallel (where possible)│
│ 5. Edge caching: Cache audio files on CDN                       │
└─────────────────────────────────────────────────────────────────┘
```

### Cost Optimization

| Service | Strategy | Est. Cost |
|---------|----------|-----------|
| **Embeddings** | Use `text-embedding-3-small` ($0.02/1M tokens) | ~$0.001/video |
| **LLM** | GPT-4o-mini for explanations ($0.15/1M input, $0.60/1M output) | ~$0.01/explanation |
| **TTS** | ElevenLabs Turbo (~$0.15/1K chars) or OpenAI TTS (~$0.015/1K chars) | ~$0.02/explanation |
| **Storage** | ChromaDB local (free) or Pinecone starter (free tier) | $0 |

**Total estimated cost per explanation: ~$0.03-0.05**

---

## 9. Assumptions & Design Decisions

1. **YouTube Transcript Availability**: Assumes videos have auto-generated or manual captions. Fallback: Whisper transcription (adds cost + latency).

2. **Chunk Size (20-40s)**: Balances context coherence with retrieval precision. Shorter chunks = more precise retrieval but less context per chunk.

3. **ChromaDB over Pinecone**: Chose local-first for development simplicity. Easy migration path to Pinecone for production scale.

4. **ElevenLabs over OpenAI TTS**: Better voice quality but higher cost. OpenAI TTS is a valid budget alternative.

5. **Python over Node.js for Backend**: Better ML/AI library ecosystem (sentence-transformers, ChromaDB native bindings). The frontend remains Next.js.

6. **No Hallucination Guarantee**: System prompt explicitly restricts LLM to retrieved context only. Combined with RAG, this minimizes (but doesn't eliminate) hallucination risk.

---

## 10. Next Steps

1. **Phase 1: Core Pipeline**
   - [ ] Implement transcript extraction (yt-dlp)
   - [ ] Build semantic chunker
   - [ ] Set up ChromaDB vector store
   - [ ] Create basic retrieval logic

2. **Phase 2: LLM Integration**
   - [ ] Prompt engineering and testing
   - [ ] Streaming response implementation
   - [ ] Response caching

3. **Phase 3: TTS Integration**
   - [ ] Set up audio synthesis
   - [ ] Audio caching and CDN

4. **Phase 4: Frontend**
   - [ ] Next.js app with explanation UI
   - [ ] Audio player component
   - [ ] Learning history

5. **Phase 5: Browser Extension**
   - [ ] Manifest V3 extension
   - [ ] YouTube integration
   - [ ] Popup UI
