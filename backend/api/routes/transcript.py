"""
Transcript ingestion API endpoint.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, File, UploadFile, Form
from typing import Optional
import uuid

from models.transcript import IngestRequest, IngestResponse, VideoStatusResponse
from services.transcript.extractor import TranscriptExtractor
from services.transcript.chunker import SemanticChunker
from services.transcript.parser import create_transcript_from_upload
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


@router.post("/upload", response_model=IngestResponse)
async def upload_transcript(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    video_id: Optional[str] = Form(None),
    video_title: Optional[str] = Form(None),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
    """
    Upload a transcript file manually.
    
    Supported formats:
    - SRT (.srt) - SubRip subtitle format
    - VTT (.vtt) - WebVTT format
    - TXT (.txt) - Plain text (will be auto-segmented)
    
    Args:
        file: Transcript file upload
        video_id: Optional custom ID (auto-generated if not provided)
        video_title: Optional title for the transcript
    """
    # Validate file type
    allowed_extensions = ['.srt', '.vtt', '.txt', '.text']
    filename = file.filename or "transcript.txt"
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else '.txt'
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
        except:
            raise HTTPException(status_code=400, detail="Could not decode file. Please use UTF-8 encoding.")
    
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    # Generate video_id if not provided
    if not video_id:
        video_id = f"upload_{uuid.uuid4().hex[:11]}"
    
    # Determine format from extension
    format_hint = ext.lstrip('.')
    if format_hint == 'text':
        format_hint = 'txt'
    
    # Parse the transcript
    transcript = create_transcript_from_upload(
        video_id=video_id,
        content=text_content,
        format_hint=format_hint,
        video_title=video_title or filename
    )
    
    if transcript.status == "error":
        raise HTTPException(status_code=400, detail=transcript.error_message)
    
    if not transcript.segments:
        raise HTTPException(status_code=400, detail="Could not parse any segments from the transcript")
    
    # Mark as processing
    video_status[video_id] = {"status": "processing", "message": "Processing uploaded transcript..."}
    
    # Queue background processing
    background_tasks.add_task(
        _process_uploaded_transcript,
        transcript=transcript,
        video_title=video_title or filename,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    
    return IngestResponse(
        status="queued",
        video_id=video_id,
        message=f"Processing {len(transcript.segments)} segments from uploaded transcript"
    )


async def _process_uploaded_transcript(
    transcript,
    video_title: str,
    embedding_service: EmbeddingService,
    vector_store: ChromaVectorStore,
):
    """Background task for processing uploaded transcript."""
    video_id = transcript.video_id
    
    try:
        video_status[video_id] = {"status": "processing", "message": "Chunking transcript..."}
        
        # Chunk semantically
        chunker = SemanticChunker(video_id=video_id)
        chunks = chunker.chunk(transcript.segments)
        
        video_status[video_id] = {
            "status": "processing",
            "message": f"Generating embeddings for {len(chunks)} chunks..."
        }
        
        # Generate embeddings
        texts = [c.text_cleaned or c.text for c in chunks]
        embeddings = await embedding_service.embed_batch(texts)
        
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        
        video_status[video_id] = {"status": "processing", "message": "Storing in vector database..."}
        
        # Store in vector database
        await vector_store.upsert_chunks(chunks, video_metadata={
            "video_id": video_id,
            "title": video_title,
            "duration": transcript.duration,
            "source": "manual_upload",
        })
        
        # Update status
        video_status[video_id] = {
            "status": "ready",
            "message": "Upload processing complete",
            "total_chunks": len(chunks),
            "title": video_title,
            "duration": transcript.duration,
        }
        
        print(f"✅ Processed uploaded transcript {video_id}: {len(chunks)} chunks")
        
    except Exception as e:
        print(f"❌ Upload processing failed for {video_id}: {e}")
        video_status[video_id] = {
            "status": "error",
            "message": str(e)
        }


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
        
        if transcript.status == "error":
            video_status[video_id] = {
                "status": "error",
                "message": transcript.error_message or "Failed to extract transcript"
            }
            return
        
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

