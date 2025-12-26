"""
Semantic transcript chunking service.
Chunks transcript by meaning + timestamps (20-40s chunks with overlap).
"""

from typing import List
import re
from datetime import datetime

from models.transcript import TranscriptChunk, RawSegment
from config.settings import settings


class SemanticChunker:
    """
    Chunks transcript by semantic meaning with timestamp awareness.
    Target: 20-40 second chunks with 5-second overlap.
    
    Design principles:
    1. Prefer natural boundaries (sentence ends, topic transitions)
    2. Never split mid-sentence if avoidable
    3. Add overlap for context continuity
    4. Mark foundational chunks that define concepts
    """
    
    def __init__(
        self,
        video_id: str,
        target_duration: float = None,
        min_duration: float = None,
        max_duration: float = None,
        overlap_duration: float = None,
    ):
        self.video_id = video_id
        self.target_duration = target_duration or settings.CHUNK_TARGET_DURATION
        self.min_duration = min_duration or settings.CHUNK_MIN_DURATION
        self.max_duration = max_duration or settings.CHUNK_MAX_DURATION
        self.overlap_duration = overlap_duration or settings.CHUNK_OVERLAP_DURATION
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]\s+')
        
        # Topic transition markers
        self.topic_markers = [
            "now let's", "next,", "moving on", "another",
            "first,", "second,", "third,", "finally,",
            "in conclusion", "the next thing", "here's",
            "so basically", "let me explain", "what is",
            "to understand", "the key", "importantly",
            "however,", "but,", "on the other hand",
            "for example", "let's look at", "consider",
        ]
        
        # Definitional patterns for foundational detection
        self.definitional_patterns = [
            r'\b(\w+)\s+is\s+(a|an|the)\s+',
            r'\bwhat\s+is\s+',
            r'\bdefined\s+as\b',
            r'\bmeans\s+that\b',
            r'\brefers\s+to\b',
            r'\bbasically\b',
            r'\bin\s+simple\s+terms\b',
            r'\bwe\s+call\s+this\b',
            r'\bthis\s+is\s+called\b',
        ]
    
    def chunk(self, segments: List[RawSegment]) -> List[TranscriptChunk]:
        """
        Main chunking algorithm:
        1. Merge tiny segments
        2. Split at natural boundaries
        3. Ensure duration constraints
        4. Add overlapping context
        """
        
        if not segments:
            return []
        
        chunks = []
        current_texts = []
        current_start = segments[0].start
        current_end = segments[0].start
        
        for segment in segments:
            potential_end = segment.end
            potential_duration = potential_end - current_start
            
            # Check if we should split
            should_split = (
                potential_duration >= self.max_duration or
                (potential_duration >= self.min_duration and 
                 self._is_natural_boundary(segment.text))
            )
            
            if should_split and current_texts:
                # Create chunk from accumulated text
                chunk_text = " ".join(current_texts)
                chunks.append(self._create_chunk(
                    text=chunk_text,
                    start=current_start,
                    end=current_end,
                    sequence=len(chunks),
                ))
                
                # Start new chunk with overlap
                # Find segments that fall within overlap window
                overlap_start = max(0, current_end - self.overlap_duration)
                overlap_texts = []
                
                for seg in segments:
                    if seg.start >= overlap_start and seg.end <= current_end:
                        overlap_texts.append(seg.text)
                    elif seg.start > current_end:
                        break
                
                current_texts = overlap_texts
                current_start = overlap_start if overlap_texts else segment.start
            
            current_texts.append(segment.text)
            current_end = segment.end
        
        # Don't forget last chunk
        if current_texts:
            chunk_text = " ".join(current_texts)
            chunks.append(self._create_chunk(
                text=chunk_text,
                start=current_start,
                end=current_end,
                sequence=len(chunks),
            ))
        
        return chunks
    
    def _is_natural_boundary(self, text: str) -> bool:
        """Check if text contains a natural topic transition."""
        text_lower = text.lower().strip()
        
        # Strong boundary: topic marker at start
        for marker in self.topic_markers:
            if text_lower.startswith(marker):
                return True
        
        return False
    
    def _create_chunk(
        self,
        text: str,
        start: float,
        end: float,
        sequence: int,
    ) -> TranscriptChunk:
        """Create a chunk with extracted metadata."""
        
        text = text.strip()
        key_terms = self._extract_key_terms(text)
        is_foundational = self._is_foundational(text, key_terms)
        
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
            is_foundational=is_foundational,
            embedding=None,  # Set later
            created_at=datetime.utcnow(),
        )
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key technical terms from text.
        Simple heuristic approach - can be enhanced with NER.
        """
        terms = []
        
        # Look for terms in definitional patterns
        for pattern in self.definitional_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    # First group is often the term being defined
                    term = match[0] if match[0] else ""
                else:
                    term = match
                if len(term) > 2 and term.isalpha():
                    terms.append(term)
        
        # Look for capitalized words (potential proper nouns / concepts)
        words = text.split()
        for i, word in enumerate(words):
            # Skip first word of sentences
            is_sentence_start = i == 0 or (i > 0 and words[i-1].endswith(('.', '!', '?')))
            
            if not is_sentence_start and word[0].isupper() and len(word) > 2:
                clean_word = re.sub(r'[^a-zA-Z]', '', word)
                if clean_word and clean_word.lower() not in terms:
                    terms.append(clean_word.lower())
        
        # Deduplicate while preserving order
        seen = set()
        unique_terms = []
        for term in terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:10]  # Limit to top 10 terms
    
    def _is_foundational(self, text: str, key_terms: List[str]) -> bool:
        """Detect if chunk defines fundamental concepts."""
        text_lower = text.lower()
        
        # Check for definitional patterns
        for pattern in self.definitional_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check for "this is", "these are" style definitions
        if re.search(r'\b(this|these)\s+(?:is|are)\s+(?:a|an|the)?\s*\w+', text_lower):
            return True
        
        # Has key terms and is early in the video (first 25%)
        # This is a heuristic - earlier content tends to be foundational
        
        return False
    
    def _clean_for_embedding(self, text: str) -> str:
        """
        Clean text for better embedding quality.
        Remove filler words, normalize, focus on semantic content.
        """
        # Lowercase
        text = text.lower()
        
        # Remove common filler words
        fillers = [
            "um", "uh", "like", "you know", "basically",
            "actually", "literally", "right", "okay", "so",
            "well", "i mean", "kind of", "sort of",
        ]
        for filler in fillers:
            text = re.sub(rf'\b{filler}\b', '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        return text.strip()
