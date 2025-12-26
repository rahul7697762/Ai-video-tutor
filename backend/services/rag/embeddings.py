"""
Embedding service for generating vector representations.
Uses OpenAI embeddings by default (text-embedding-3-small).
"""

from typing import List
import asyncio
from openai import AsyncOpenAI
import tiktoken

from config.settings import settings


class EmbeddingService:
    """
    Generate embeddings for text chunks.
    
    Uses OpenAI's text-embedding-3-small model by default:
    - 1536 dimensions
    - ~$0.02 per 1M tokens
    - Good balance of cost and quality
    """
    
    def __init__(
        self,
        model: str = None,
        dimensions: int = None,
    ):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Token counting for cost estimation
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Rate limiting
        self.max_tokens_per_batch = 8000
        self.max_texts_per_batch = 100
    
    async def embed(self, text: str) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text.strip():
            return [0.0] * self.dimensions
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"Embedding error: {e}")
            # Return zero vector on error (will have low similarity to real embeddings)
            return [0.0] * self.dimensions
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts in batches.
        Optimized for throughput while respecting rate limits.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Split into batches respecting token limits
        batches = self._create_batches(texts)
        
        all_embeddings = []
        
        for batch_texts in batches:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch_texts,
                    dimensions=self.dimensions,
                )
                
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [item.embedding for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"Batch embedding error: {e}")
                # Return zero vectors for failed batch
                all_embeddings.extend([[0.0] * self.dimensions] * len(batch_texts))
            
            # Small delay between batches to avoid rate limits
            if len(batches) > 1:
                await asyncio.sleep(0.1)
        
        return all_embeddings
    
    def _create_batches(self, texts: List[str]) -> List[List[str]]:
        """Split texts into batches respecting token limits."""
        batches = []
        current_batch = []
        current_tokens = 0
        
        for text in texts:
            # Clean empty texts
            if not text.strip():
                text = " "  # OpenAI needs non-empty input
            
            text_tokens = len(self.tokenizer.encode(text))
            
            # Check if adding this text would exceed limits
            would_exceed_tokens = current_tokens + text_tokens > self.max_tokens_per_batch
            would_exceed_count = len(current_batch) >= self.max_texts_per_batch
            
            if current_batch and (would_exceed_tokens or would_exceed_count):
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0
            
            current_batch.append(text)
            current_tokens += text_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for cost estimation."""
        return len(self.tokenizer.encode(text))
    
    def estimate_cost(self, texts: List[str]) -> float:
        """
        Estimate embedding cost in USD.
        text-embedding-3-small: $0.02 per 1M tokens
        """
        total_tokens = sum(self.count_tokens(t) for t in texts)
        cost_per_token = 0.02 / 1_000_000
        return total_tokens * cost_per_token


def extract_key_terms(text: str) -> List[str]:
    """
    Extract key terms from text for metadata.
    Used by chunker to identify important concepts.
    
    This is a simple keyword extraction - can be enhanced with:
    - spaCy NER
    - KeyBERT
    - TF-IDF
    """
    import re
    
    # Simple approach: find capitalized multi-word phrases and technical terms
    terms = []
    
    # Match capitalized words/phrases
    cap_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    caps = re.findall(cap_pattern, text)
    terms.extend([c.lower() for c in caps if len(c) > 3])
    
    # Match common technical suffixes
    tech_pattern = r'\b\w+(?:tion|ment|ity|ness|ing|ism|ist)\b'
    tech = re.findall(tech_pattern, text.lower())
    terms.extend([t for t in tech if len(t) > 5])
    
    # Deduplicate
    return list(set(terms))[:10]
