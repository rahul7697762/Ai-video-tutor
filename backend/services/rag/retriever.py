"""
Multi-strategy retrieval service for RAG.
Implements three-pronged retrieval: temporal, foundational, and semantic.
"""

from typing import List, Set
from enum import Enum

from models.explanation import ExplanationChunk
from services.rag.vector_store import ChromaVectorStore, get_vector_store
from services.rag.embeddings import EmbeddingService
from config.settings import settings


class RetrievalStrategy(Enum):
    """Types of retrieval strategies."""
    TEMPORAL = "temporal"           # Chunks around timestamp
    FOUNDATIONAL = "foundational"   # Definition chunks
    SEMANTIC = "semantic"           # Similarity search


# Global retriever instance
_retriever = None


def get_retriever() -> "MultiStrategyRetriever":
    """Get or create the global retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = MultiStrategyRetriever(
            vector_store=get_vector_store(),
            embedding_service=EmbeddingService(),
        )
    return _retriever


class MultiStrategyRetriever:
    """
    Three-pronged retrieval strategy for optimal context:
    
    1. TEMPORAL: Chunks within ±60s of the pause timestamp
       - Most relevant to what the user is watching
       - Highest priority
       
    2. FOUNDATIONAL: Earlier chunks that define terms used at timestamp
       - Provides prerequisite knowledge
       - Only looks at chunks BEFORE current position
       
    3. SEMANTIC: Similar content from anywhere in video
       - Catches related concepts mentioned elsewhere
       - Fills remaining context slots
    
    The retrieved chunks are combined and sorted by timestamp
    to maintain the video's teaching flow.
    """
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_service: EmbeddingService,
        temporal_window: float = None,
        max_chunks_per_strategy: int = None,
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.temporal_window = temporal_window or settings.RETRIEVAL_TEMPORAL_WINDOW
        self.max_per_strategy = max_chunks_per_strategy or settings.RETRIEVAL_MAX_PER_STRATEGY
    
    async def retrieve(
        self,
        video_id: str,
        timestamp: float,
        query: str = None,
        max_total_chunks: int = None,
    ) -> List[ExplanationChunk]:
        """
        Execute multi-strategy retrieval and merge results.
        
        Args:
            video_id: YouTube video ID
            timestamp: Pause position in seconds
            query: Optional user query (e.g., "I don't understand this")
            max_total_chunks: Maximum chunks to return
            
        Returns:
            List of ExplanationChunk sorted by timestamp
        """
        max_total = max_total_chunks or settings.RETRIEVAL_MAX_CHUNKS
        results = []
        seen_chunk_ids: Set[str] = set()
        
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
                if hasattr(chunk, 'key_terms') and chunk.key_terms:
                    temporal_terms.update(chunk.key_terms)
            
            if temporal_terms:
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
        context_text = " ".join([c.text for c in temporal_chunks[:2]]) if temporal_chunks else ""
        search_query = f"{query or 'explain this concept'} {context_text}".strip()
        
        semantic_chunks = await self._retrieve_semantic(
            video_id=video_id,
            query=search_query,
            exclude_ids=seen_chunk_ids,
        )
        
        remaining_slots = max_total - len(results)
        for chunk in semantic_chunks[:remaining_slots]:
            if chunk.chunk_id not in seen_chunk_ids:
                chunk.relevance_type = "semantic"
                results.append(chunk)
                seen_chunk_ids.add(chunk.chunk_id)
        
        # Sort by timestamp for coherent context (teaching flow)
        results.sort(key=lambda x: x.start_time)
        
        return results[:max_total]
    
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
        start = max(0, timestamp - window)
        end = timestamp + window
        
        chunks = await self.vector_store.query_by_time_range(
            video_id=video_id,
            start=start,
            end=end,
            order_by_distance_to=timestamp,  # Closest to pause point first
        )
        
        return chunks
    
    async def _retrieve_foundational(
        self,
        video_id: str,
        terms: List[str],
        before_timestamp: float,
    ) -> List[ExplanationChunk]:
        """
        Find chunks that define the given terms.
        Only looks at chunks BEFORE the current timestamp.
        
        Foundational chunks:
        - Are marked as is_foundational=True
        - Appear earlier in the video
        - Contain definitional language
        """
        chunks = await self.vector_store.query_by_metadata(
            video_id=video_id,
            is_foundational=True,
            before_timestamp=before_timestamp,
            key_terms=terms,
            limit=self.max_per_strategy * 2,  # Extra for filtering
        )
        
        # Score by term overlap
        scored_chunks = []
        terms_lower = set(t.lower() for t in terms if t)
        
        for chunk in chunks:
            score = 0
            chunk_text_lower = chunk.text.lower()
            
            for term in terms_lower:
                if term in chunk_text_lower:
                    score += 1
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by score descending, then by timestamp (earlier first)
        scored_chunks.sort(key=lambda x: (-x[0], x[1].start_time))
        
        return [chunk for _, chunk in scored_chunks]
    
    async def _retrieve_semantic(
        self,
        video_id: str,
        query: str,
        exclude_ids: Set[str],
    ) -> List[ExplanationChunk]:
        """
        Vector similarity search across entire transcript.
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed(query)
        
        # Search with extra results for filtering
        results = await self.vector_store.similarity_search(
            video_id=video_id,
            query_embedding=query_embedding,
            top_k=self.max_per_strategy * 3,
        )
        
        # Filter out already-retrieved chunks
        filtered = [r for r in results if r.chunk_id not in exclude_ids]
        
        # Sort by similarity score
        filtered.sort(key=lambda x: x.similarity_score or 0, reverse=True)
        
        return filtered
