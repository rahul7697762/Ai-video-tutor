"""
Quick test script to verify backend setup.
Run with: python -m pytest tests/ -v
Or: python tests/test_quick.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_transcript_extractor():
    """Test YouTube transcript extraction."""
    from services.transcript.extractor import TranscriptExtractor
    
    print("\n🧪 Testing Transcript Extractor...")
    
    extractor = TranscriptExtractor()
    
    # Test with a known video (Rick Astley - Never Gonna Give You Up)
    # This video has captions available
    test_video_id = "dQw4w9WgXcQ"
    
    try:
        transcript = await extractor.extract(test_video_id)
        
        if transcript.status == "ready" and transcript.segments:
            print(f"   ✅ Extracted {len(transcript.segments)} segments")
            print(f"   📊 Duration: {transcript.duration:.1f}s")
            print(f"   📝 First segment: '{transcript.segments[0].text[:50]}...'")
            return True
        else:
            print(f"   ❌ Extraction failed: {transcript.error_message}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_chunker():
    """Test semantic chunking."""
    from services.transcript.chunker import SemanticChunker
    from models.transcript import RawSegment
    
    print("\n🧪 Testing Semantic Chunker...")
    
    # Create mock segments
    segments = [
        RawSegment(text="Hello everyone, welcome to this tutorial.", start=0, duration=3),
        RawSegment(text="Today we're going to learn about machine learning.", start=3, duration=4),
        RawSegment(text="Machine learning is a type of artificial intelligence.", start=7, duration=5),
        RawSegment(text="It allows computers to learn from data.", start=12, duration=4),
        RawSegment(text="Now let's look at neural networks.", start=16, duration=3),
        RawSegment(text="Neural networks are inspired by the human brain.", start=19, duration=5),
        RawSegment(text="They consist of layers of neurons.", start=24, duration=4),
    ]
    
    chunker = SemanticChunker(video_id="test123")
    # Adjust for test (smaller durations)
    chunker.min_duration = 5
    chunker.max_duration = 15
    chunker.target_duration = 10
    
    try:
        chunks = chunker.chunk(segments)
        
        print(f"   ✅ Created {len(chunks)} chunks from {len(segments)} segments")
        for chunk in chunks:
            print(f"   📦 Chunk {chunk.sequence}: {chunk.start_time:.1f}s - {chunk.end_time:.1f}s ({len(chunk.text)} chars)")
            if chunk.is_foundational:
                print(f"       🔖 Foundational: {chunk.key_terms}")
        
        return len(chunks) > 0
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_embeddings():
    """Test embedding generation."""
    from services.rag.embeddings import EmbeddingService
    from config.settings import settings
    
    print("\n🧪 Testing Embedding Service...")
    
    if not settings.OPENAI_API_KEY:
        print("   ⚠️ OPENAI_API_KEY not set, skipping embedding test")
        return True
    
    service = EmbeddingService()
    
    try:
        # Test single embedding
        text = "Machine learning is a subset of artificial intelligence."
        embedding = await service.embed(text)
        
        print(f"   ✅ Generated embedding with {len(embedding)} dimensions")
        print(f"   📊 First 5 values: {embedding[:5]}")
        
        # Test batch
        texts = [
            "Neural networks are computational models.",
            "Deep learning uses multiple layers.",
        ]
        embeddings = await service.embed_batch(texts)
        
        print(f"   ✅ Batch embedded {len(embeddings)} texts")
        
        return len(embedding) == 1536 and len(embeddings) == 2
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_vector_store():
    """Test ChromaDB vector store."""
    from services.rag.vector_store import ChromaVectorStore
    from models.transcript import TranscriptChunk
    from datetime import datetime
    
    print("\n🧪 Testing Vector Store...")
    
    # Use a test directory
    store = ChromaVectorStore(persist_directory="./data/chroma_test")
    
    try:
        # Create test chunks
        chunks = [
            TranscriptChunk(
                chunk_id="test_0.0_0",
                video_id="test123",
                sequence=0,
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                text="Introduction to machine learning concepts.",
                key_terms=["machine learning"],
                is_foundational=True,
                embedding=[0.1] * 1536,  # Mock embedding
                created_at=datetime.utcnow(),
            ),
            TranscriptChunk(
                chunk_id="test_30.0_1",
                video_id="test123",
                sequence=1,
                start_time=30.0,
                end_time=60.0,
                duration=30.0,
                text="Neural networks are powerful tools.",
                key_terms=["neural networks"],
                is_foundational=False,
                embedding=[0.2] * 1536,
                created_at=datetime.utcnow(),
            ),
        ]
        
        # Test upsert
        await store.upsert_chunks(chunks)
        print("   ✅ Upserted 2 chunks")
        
        # Test video exists
        exists = await store.video_exists("test123")
        print(f"   ✅ Video exists check: {exists}")
        
        # Test time range query
        results = await store.query_by_time_range("test123", 0, 60)
        print(f"   ✅ Time range query returned {len(results)} chunks")
        
        # Cleanup
        await store.delete_video("test123")
        print("   ✅ Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_tests():
    """Run all tests."""
    print("=" * 50)
    print("🚀 YouTube Learning Assistant - Backend Tests")
    print("=" * 50)
    
    results = []
    
    # Test transcript extraction
    results.append(("Transcript Extractor", await test_transcript_extractor()))
    
    # Test chunker
    results.append(("Semantic Chunker", await test_chunker()))
    
    # Test embeddings (requires API key)
    results.append(("Embedding Service", await test_embeddings()))
    
    # Test vector store
    results.append(("Vector Store", await test_vector_store()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
