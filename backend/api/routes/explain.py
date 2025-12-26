"""
Explanation API endpoint.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import time
import json
from typing import AsyncGenerator

from models.explanation import ExplainRequest, ExplainResponse, ExplanationChunk
from services.rag.retriever import MultiStrategyRetriever, get_retriever
from services.rag.vector_store import get_vector_store, ChromaVectorStore
from services.llm.tutor import TutorLLM, get_tutor_llm
from services.llm.prompts import TutorPrompts
from services.tts.synthesizer import TTSService, get_tts_service
from api.routes.transcript import video_status

router = APIRouter(prefix="/api/explain", tags=["explain"])


@router.post("", response_model=ExplainResponse)
async def explain_timestamp(
    request: ExplainRequest,
    retriever: MultiStrategyRetriever = Depends(get_retriever),
    llm_service: TutorLLM = Depends(get_tutor_llm),
    tts_service: TTSService = Depends(get_tts_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
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
    if request.video_id in video_status:
        status_info = video_status[request.video_id]
        status = status_info.get("status")
        if status != "ready":
            # Include the actual error message if available
            error_msg = status_info.get("message", "Unknown error")
            if status == "error":
                raise HTTPException(
                    status_code=400,
                    detail=f"This video cannot be processed: {error_msg}"
                )
            elif status == "processing":
                raise HTTPException(
                    status_code=400,
                    detail="Video is still being processed. Please wait a moment."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video not ready. Status: {status}. Call /transcript/ingest first."
                )
    else:
        # Check vector store
        existing = await vector_store.video_exists(request.video_id)
        if not existing:
            raise HTTPException(
                status_code=400,
                detail="Video not yet ingested. Call /transcript/ingest first."
            )
    
    # 2. Retrieve relevant chunks using multi-strategy retrieval
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
        # Simplify explanation for natural speech
        spoken_text = await llm_service.generate(
            system_prompt="You are a text formatter. Convert markdown to natural speech.",
            user_prompt=TutorPrompts.AUDIO_SIMPLIFICATION_PROMPT.format(
                explanation=explanation
            ),
        )
        
        # Generate TTS
        audio_result = await tts_service.synthesize(
            text=spoken_text,
            video_id=request.video_id,
            timestamp=request.timestamp,
        )
        
        if audio_result:
            audio_url, audio_duration = audio_result
    
    # 5. Extract summary (first paragraph or section)
    summary = _extract_summary(explanation)
    
    # 6. Determine primary topic
    primary_topic = "General"
    if chunks and chunks[0].key_terms:
        primary_topic = chunks[0].key_terms[0]
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return ExplainResponse(
        explanation=explanation,
        summary=summary,
        audio_url=audio_url,
        audio_duration=audio_duration,
        retrieved_chunks=[
            ExplanationChunk(
                chunk_id=c.chunk_id,
                text=c.text[:200] + "..." if len(c.text) > 200 else c.text,
                start_time=c.start_time,
                end_time=c.end_time,
                relevance_type=c.relevance_type,
                similarity_score=c.similarity_score,
            ) for c in chunks
        ],
        primary_topic=primary_topic,
        timestamp=request.timestamp,
        processing_time_ms=processing_time,
    )


@router.post("/stream")
async def explain_timestamp_stream(
    request: ExplainRequest,
    retriever: MultiStrategyRetriever = Depends(get_retriever),
    llm_service: TutorLLM = Depends(get_tutor_llm),
    tts_service: TTSService = Depends(get_tts_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
    """
    SSE streaming version for lower perceived latency.
    Streams explanation tokens as they're generated.
    """
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Check video status
            if request.video_id in video_status:
                status = video_status[request.video_id].get("status")
                if status != "ready":
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Video not ready: {status}'})}\n\n"
                    return
            else:
                existing = await vector_store.video_exists(request.video_id)
                if not existing:
                    yield f"data: {json.dumps({'type': 'error', 'content': 'Video not ingested'})}\n\n"
                    return
            
            # Retrieve chunks
            chunks = await retriever.retrieve(
                video_id=request.video_id,
                timestamp=request.timestamp,
                query=request.user_query,
                max_total_chunks=request.max_chunks,
            )
            
            if not chunks:
                yield f"data: {json.dumps({'type': 'error', 'content': 'No transcript found'})}\n\n"
                return
            
            # Send context info
            yield f"data: {json.dumps({'type': 'context', 'chunks': len(chunks)})}\n\n"
            
            # Build prompt
            prompt = TutorPrompts.build_explanation_prompt(
                chunks=chunks,
                timestamp=request.timestamp,
                user_query=request.user_query,
            )
            
            # Stream explanation tokens
            full_explanation = ""
            async for token in llm_service.generate_stream(
                system_prompt=TutorPrompts.SYSTEM_PROMPT,
                user_prompt=prompt,
            ):
                full_explanation += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Generate audio if requested
            if request.include_audio:
                yield f"data: {json.dumps({'type': 'audio_start'})}\n\n"
                
                spoken_text = await llm_service.generate(
                    system_prompt="You are a text formatter.",
                    user_prompt=TutorPrompts.AUDIO_SIMPLIFICATION_PROMPT.format(
                        explanation=full_explanation
                    ),
                )
                
                audio_result = await tts_service.synthesize(
                    text=spoken_text,
                    video_id=request.video_id,
                    timestamp=request.timestamp,
                )
                
                if audio_result:
                    audio_url, audio_duration = audio_result
                    yield f"data: {json.dumps({'type': 'audio', 'url': audio_url, 'duration': audio_duration})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def _extract_summary(explanation: str) -> str:
    """Extract a brief summary from the explanation."""
    # Look for the "What's Being Discussed" section
    lines = explanation.split("\n")
    
    for i, line in enumerate(lines):
        if "what's being discussed" in line.lower() or "🎯" in line:
            # Return the next non-empty line
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    return lines[j].strip()[:200]
    
    # Fallback: first paragraph
    paragraphs = explanation.split("\n\n")
    for para in paragraphs:
        clean = para.strip()
        if clean and not clean.startswith("#") and len(clean) > 20:
            return clean[:200]
    
    return explanation[:200]
