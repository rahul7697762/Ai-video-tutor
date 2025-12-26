"""
Transcript ingestion API endpoint.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Optional

from models.transcript import IngestRequest, IngestResponse, VideoStatusResponse
from services.transcript.extractor import TranscriptExtractor
from services.transcript.chunker import SemanticChunker
from services.rag.embeddings import EmbeddingService
from services.rag.vector_store import get_vector_store, ChromaVectorStore

router = APIRouter(prefix="/api/transcript", tags=["transcript"])

# In-memory status tracking (use Redis in production)
video_status: dict = {}


def get_transcript_extractor() -> TranscriptExtractor:
    return TranscriptExtractor()


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_transcript(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    extractor: TranscriptExtractor = Depends(get_transcript_extractor),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
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
    video_id = request.video_id
    
    # Check if already processing
    if video_id in video_status and video_status[video_id]["status"] == "processing":
        return IngestResponse(
            status="processing",
            video_id=video_id,
            message="Video is currently being processed"
        )
    
    # Check if already indexed (unless force refresh)
    if not request.force_refresh:
        existing = await vector_store.video_exists(video_id)
        if existing:
            return IngestResponse(
                status="exists",
                video_id=video_id,
                message="Video already ingested",
                total_chunks=existing.get("total_chunks", 0)
            )
    
    # Mark as processing
    video_status[video_id] = {"status": "processing", "message": "Starting ingestion..."}
    
    # Queue background processing
    background_tasks.add_task(
        _process_ingestion,
        video_id=video_id,
        extractor=extractor,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    
    return IngestResponse(
        status="queued",
        video_id=video_id,
        message="Ingestion started in background"
    )


async def _process_ingestion(
    video_id: str,
    extractor: TranscriptExtractor,
    embedding_service: EmbeddingService,
    vector_store: ChromaVectorStore,
):
    """Background task for full ingestion pipeline."""
    
    try:
        video_status[video_id] = {"status": "processing", "message": "Extracting transcript..."}
        
        # 1. Extract transcript from YouTube
        transcript = await extractor.extract(video_id)
        
        if not transcript.segments:
            video_status[video_id] = {
                "status": "error",
                "message": "No transcript available for this video"
            }
            return
        
        video_status[video_id] = {"status": "processing", "message": "Chunking transcript..."}
        
        # 2. Chunk semantically
        chunker = SemanticChunker(video_id=video_id)
        chunks = chunker.chunk(transcript.segments)
        
        video_status[video_id] = {
            "status": "processing",
            "message": f"Generating embeddings for {len(chunks)} chunks..."
        }
        
        # 3. Generate embeddings (batch for efficiency)
        texts = [c.text_cleaned or c.text for c in chunks]
        embeddings = await embedding_service.embed_batch(texts)
        
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        
        video_status[video_id] = {"status": "processing", "message": "Storing in vector database..."}
        
        # 4. Store in vector database
        await vector_store.upsert_chunks(chunks, video_metadata={
            "video_id": video_id,
            "title": transcript.title,
            "duration": transcript.duration,
        })
        
        # 5. Update status
        video_status[video_id] = {
            "status": "ready",
            "message": "Ingestion complete",
            "total_chunks": len(chunks),
            "title": transcript.title,
            "duration": transcript.duration,
        }
        
        print(f"✅ Ingested {video_id}: {len(chunks)} chunks")
        
    except Exception as e:
        print(f"❌ Ingestion failed for {video_id}: {e}")
        video_status[video_id] = {
            "status": "error",
            "message": str(e)
        }


@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def get_video_status(video_id: str):
    """Get the ingestion status of a video."""
    
    if video_id in video_status:
        status_info = video_status[video_id]
        return VideoStatusResponse(
            video_id=video_id,
            status=status_info["status"],
            total_chunks=status_info.get("total_chunks"),
            title=status_info.get("title"),
            duration=status_info.get("duration"),
        )
    
    # Check vector store
    vector_store = get_vector_store()
    existing = await vector_store.video_exists(video_id)
    
    if existing:
        return VideoStatusResponse(
            video_id=video_id,
            status="ready",
            total_chunks=existing.get("total_chunks", 0),
        )
    
    return VideoStatusResponse(
        video_id=video_id,
        status="not_found",
    )
