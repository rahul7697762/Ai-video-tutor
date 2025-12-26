"""
YouTube transcript extraction service.
Uses youtube-transcript-api as primary source.
"""

import os
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import re

from models.transcript import VideoTranscript, RawSegment


class TranscriptExtractor:
    """
    Extracts transcripts from YouTube videos.
    
    Uses youtube-transcript-api which works well on cloud servers.
    """
    
    def __init__(self):
        self.preferred_languages = ["en", "en-US", "en-GB", "en-IN"]
        # Create instance of the API (new version uses instance methods)
        self.ytt_api = YouTubeTranscriptApi()
    
    async def extract(self, video_id: str) -> VideoTranscript:
        """
        Extract transcript from a YouTube video.
        
        Args:
            video_id: 11-character YouTube video ID
            
        Returns:
            VideoTranscript with segments populated
        """
        
        # Validate video ID format
        if not self._is_valid_video_id(video_id):
            raise ValueError(f"Invalid video ID format: {video_id}")
        
        transcript = VideoTranscript(
            video_id=video_id,
            source="youtube_api",
        )
        
        try:
            # Extract using YouTube Transcript API
            segments = await self._extract_youtube_api(video_id)
            
            if not segments:
                transcript.status = "error"
                transcript.error_message = "No transcript segments found"
                return transcript
                
            transcript.segments = segments
            transcript.status = "ready"
            
            # Calculate duration from last segment
            if segments:
                last = segments[-1]
                transcript.duration = last.start + last.duration
                
        except TranscriptsDisabled:
            transcript.status = "error"
            transcript.error_message = "Transcripts are disabled for this video"
            
        except NoTranscriptFound:
            transcript.status = "error"
            transcript.error_message = "No English transcript found for this video"
            
        except VideoUnavailable:
            transcript.status = "error"
            transcript.error_message = "Video is unavailable or private"
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific YouTube/network errors
            if "too many requests" in error_msg or "429" in error_msg:
                transcript.status = "error"
                transcript.error_message = "Rate limited by YouTube. Please try again in a few minutes."
            elif "sign in" in error_msg or "bot" in error_msg:
                transcript.status = "error"
                transcript.error_message = "YouTube requires authentication. Please try a different video."
            else:
                transcript.status = "error"
                transcript.error_message = f"Failed to extract transcript: {str(e)}"
        
        return transcript
    
    async def _extract_youtube_api(self, video_id: str) -> list[RawSegment]:
        """Extract using youtube-transcript-api (new version with instance methods)."""
        
        segments = []
        
        # Try to list available transcripts first
        try:
            transcript_list = self.ytt_api.list(video_id)
            
            # Try to find preferred language transcript
            selected_transcript = None
            for t in transcript_list:
                if t.language_code in self.preferred_languages:
                    selected_transcript = t
                    break
            
            # If no preferred language found, try to find any English variant
            if selected_transcript is None:
                for t in transcript_list:
                    if t.language_code.startswith("en"):
                        selected_transcript = t
                        break
            
            # If still no English, use the first available
            if selected_transcript is None and transcript_list:
                selected_transcript = transcript_list[0]
            
            if selected_transcript:
                # Fetch the full transcript data
                result = self.ytt_api.fetch(video_id, languages=[selected_transcript.language_code])
            else:
                # Fallback: try fetching directly with preferred languages
                result = self.ytt_api.fetch(video_id, languages=self.preferred_languages)
                
        except Exception:
            # Fallback: try fetching with default language
            result = self.ytt_api.fetch(video_id)
        
        # Convert snippets to segments
        for snippet in result.snippets:
            segments.append(RawSegment(
                text=self._clean_text(snippet.text),
                start=snippet.start,
                duration=getattr(snippet, 'duration', 0),
            ))
        
        return segments
    
    def _clean_text(self, text: str) -> str:
        """Clean transcript text."""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        
        # Remove [Music], [Applause] style markers
        text = re.sub(r"\[[^\]]+\]", "", text)
        
        # Normalize whitespace
        text = " ".join(text.split())
        
        return text.strip()
    
    def _is_valid_video_id(self, video_id: str) -> bool:
        """Validate YouTube video ID format."""
        # YouTube IDs are 11 characters, alphanumeric with - and _
        if len(video_id) != 11:
            return False
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", video_id))
    
    async def get_video_info(self, video_id: str) -> dict:
        """Get basic video metadata (without yt-dlp to avoid rate limits)."""
        # Return minimal info - actual metadata can be fetched client-side
        return {
            "title": "",
            "channel": "",
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        }

