"""
Vector store service using ChromaDB.
Handles storage and retrieval of transcript chunk embeddings.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from models.transcript import TranscriptChunk
from models.explanation import ExplanationChunk
from config.settings import settings


# Global vector store instance
_vector_store = None


def get_vector_store() -> "ChromaVectorStore":
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore()
    return _vector_store


class ChromaVectorStore:
    """
    ChromaDB-based vector store with metadata filtering.
    
    Why ChromaDB:
    - Runs locally (no external service needed for dev)
    - Built-in metadata filtering
    - Persistent storage
    - Easy migration path to Pinecone/Weaviate later
    
    Collection schema:
    - id: chunk_id
    - embedding: vector (1536 dim)
    - document: chunk text
    - metadata: video_id, start_time, end_time, sequence, is_foundational, key_terms
    """
    
    def __init__(self, persist_directory: str = None):
        persist_dir = persist_directory or settings.CHROMA_PERSIST_DIR
        
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )
        
        self.collection = self.client.get_or_create_collection(
            name="youtube_transcripts",
            metadata={"hnsw:space": "cosine"},  # Cosine similarity
        )
        
        # Track ingested videos (in-memory cache)
        self._video_cache: Dict[str, Dict] = {}
    
    async def upsert_chunks(
        self,
        chunks: List[TranscriptChunk],
        video_metadata: Dict[str, Any] = None,
    ) -> None:
        """
        Store chunks with embeddings and metadata.
        
        Args:
            chunks: List of transcript chunks with embeddings
            video_metadata: Optional video-level metadata (title, duration)
        """
        if not chunks:
            return
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            
            ids.append(chunk.chunk_id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.text)
            metadatas.append({
                "video_id": chunk.video_id,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "sequence": chunk.sequence,
                "duration": chunk.duration,
                "is_foundational": chunk.is_foundational,
                "key_terms": ",".join(chunk.key_terms),  # ChromaDB needs strings
            })
        
        if not ids:
            return
        
        # Upsert to collection
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        
        # Update video cache
        video_id = chunks[0].video_id
        self._video_cache[video_id] = {
            "total_chunks": len(chunks),
            **(video_metadata or {}),
        }
    
    async def video_exists(self, video_id: str) -> Optional[Dict]:
        """
        Check if a video has been ingested.
        
        Returns:
            Dict with video info if exists, None otherwise
        """
        # Check cache first
        if video_id in self._video_cache:
            return self._video_cache[video_id]
        
        # Query collection
        results = self.collection.get(
            where={"video_id": {"$eq": video_id}},
            limit=1,
        )
        
        if results["ids"]:
            # Get chunk count
            all_results = self.collection.get(
                where={"video_id": {"$eq": video_id}},
            )
            
            info = {"total_chunks": len(all_results["ids"])}
            self._video_cache[video_id] = info
            return info
        
        return None
    
    async def query_by_time_range(
        self,
        video_id: str,
        start: float,
        end: float,
        order_by_distance_to: float = None,
    ) -> List[ExplanationChunk]:
        """
        Retrieve chunks within a time range.
        
        Args:
            video_id: YouTube video ID
            start: Start timestamp (seconds)
            end: End timestamp (seconds)
            order_by_distance_to: Optional timestamp to order results by proximity
            
        Returns:
            List of ExplanationChunk objects
        """
        # ChromaDB where clause for time range
        results = self.collection.get(
            where={
                "$and": [
                    {"video_id": {"$eq": video_id}},
                    {"start_time": {"$gte": start}},
                    {"end_time": {"$lte": end}},
                ]
            },
            include=["documents", "metadatas"],
        )
        
        chunks = self._results_to_chunks(results, relevance_type="temporal")
        
        # Sort by distance to target timestamp if specified
        if order_by_distance_to is not None:
            chunks.sort(
                key=lambda c: abs(c.start_time - order_by_distance_to)
            )
        else:
            chunks.sort(key=lambda c: c.start_time)
        
        return chunks
    
    async def query_by_metadata(
        self,
        video_id: str,
        is_foundational: bool = None,
        before_timestamp: float = None,
        key_terms: List[str] = None,
        limit: int = 10,
    ) -> List[ExplanationChunk]:
        """
        Query chunks by metadata filters.
        
        Used for finding foundational chunks that define terms.
        """
        # Build where clause
        conditions = [{"video_id": {"$eq": video_id}}]
        
        if is_foundational is not None:
            conditions.append({"is_foundational": {"$eq": is_foundational}})
        
        if before_timestamp is not None:
            conditions.append({"end_time": {"$lt": before_timestamp}})
        
        where_clause = {"$and": conditions} if len(conditions) > 1 else conditions[0]
        
        results = self.collection.get(
            where=where_clause,
            include=["documents", "metadatas"],
        )
        
        chunks = self._results_to_chunks(results, relevance_type="foundational")
        
        # Filter by key terms if specified
        if key_terms:
            key_terms_set = set(t.lower() for t in key_terms)
            filtered = []
            for chunk in chunks:
                chunk_terms = set(chunk.key_terms) if hasattr(chunk, 'key_terms') else set()
                # Check metadata for key_terms
                if any(term in chunk.text.lower() for term in key_terms_set):
                    filtered.append(chunk)
            chunks = filtered
        
        # Sort by sequence (earlier first)
        chunks.sort(key=lambda c: c.start_time)
        
        return chunks[:limit]
    
    async def similarity_search(
        self,
        video_id: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[ExplanationChunk]:
        """
        Semantic similarity search using vector embeddings.
        
        Args:
            video_id: YouTube video ID
            query_embedding: Query vector
            top_k: Number of results to return
            
        Returns:
            List of ExplanationChunk objects with similarity scores
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where={"video_id": {"$eq": video_id}},
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        
        chunks = []
        
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                document = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Convert distance to similarity (cosine distance to similarity)
                similarity = 1 - distance
                
                chunk = ExplanationChunk(
                    chunk_id=chunk_id,
                    text=document,
                    start_time=metadata.get("start_time", 0),
                    end_time=metadata.get("end_time", 0),
                    relevance_type="semantic",
                    similarity_score=similarity,
                    key_terms=[t.strip() for t in metadata.get("key_terms", "").split(",") if t.strip()],
                )
                chunks.append(chunk)
        
        return chunks
    
    async def delete_video(self, video_id: str) -> int:
        """
        Delete all chunks for a video.
        
        Returns:
            Number of chunks deleted
        """
        # Get all chunk IDs for this video
        results = self.collection.get(
            where={"video_id": {"$eq": video_id}},
        )
        
        if not results["ids"]:
            return 0
        
        # Delete chunks
        self.collection.delete(ids=results["ids"])
        
        # Clear cache
        if video_id in self._video_cache:
            del self._video_cache[video_id]
        
        return len(results["ids"])
    
    def _results_to_chunks(
        self,
        results: Dict,
        relevance_type: str = "unknown",
    ) -> List[ExplanationChunk]:
        """Convert ChromaDB results to ExplanationChunk objects."""
        chunks = []
        
        if not results["ids"]:
            return chunks
        
        for i, chunk_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i] if results.get("metadatas") else {}
            document = results["documents"][i] if results.get("documents") else ""
            
            chunk = ExplanationChunk(
                chunk_id=chunk_id,
                text=document,
                start_time=metadata.get("start_time", 0),
                end_time=metadata.get("end_time", 0),
                relevance_type=relevance_type,
                similarity_score=None,
                key_terms=[t.strip() for t in metadata.get("key_terms", "").split(",") if t.strip()],
            )
            chunks.append(chunk)
        
        return chunks
