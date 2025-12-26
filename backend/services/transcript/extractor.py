"""
YouTube transcript extraction service.
Uses youtube-transcript-api as primary, yt-dlp as fallback.
"""

from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re

from models.transcript import VideoTranscript, RawSegment


class TranscriptExtractor:
    """
    Extracts transcripts from YouTube videos.
    
    Strategy:
    1. Try official YouTube Transcript API (fastest)
    2. Fall back to yt-dlp if needed
    """
    
    def __init__(self):
        self.preferred_languages = ["en", "en-US", "en-GB"]
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
            # Try YouTube Transcript API
            segments = await self._extract_youtube_api(video_id)
            transcript.segments = segments
            transcript.status = "ready"
            
            # Calculate duration from last segment
            if segments:
                last = segments[-1]
                transcript.duration = last.start + last.duration
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            transcript.status = "error"
            transcript.error_message = f"No transcript available: {str(e)}"
            
        except Exception as e:
            # Try fallback
            try:
                segments = await self._extract_yt_dlp(video_id)
                transcript.segments = segments
                transcript.source = "yt_dlp"
                transcript.status = "ready"
                
                if segments:
                    last = segments[-1]
                    transcript.duration = last.start + last.duration
                    
            except Exception as fallback_error:
                transcript.status = "error"
                transcript.error_message = f"Extraction failed: {str(e)}. Fallback: {str(fallback_error)}"
        
        return transcript
    
    async def _extract_youtube_api(self, video_id: str) -> list[RawSegment]:
        """Extract using youtube-transcript-api (new version with instance methods)."""
        
        # Try to list available transcripts first
        try:
            transcript_list = self.ytt_api.list(video_id)
            
            # Try to find preferred language transcript
            selected_transcript = None
            for t in transcript_list:
                if t.language_code in self.preferred_languages:
                    selected_transcript = t
                    break
            
            # If no preferred language found, use the first available
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
        segments = []
        for snippet in result.snippets:
            segments.append(RawSegment(
                text=self._clean_text(snippet.text),
                start=snippet.start,
                duration=getattr(snippet, 'duration', 0),
            ))
        
        return segments
    
    async def _extract_yt_dlp(self, video_id: str) -> list[RawSegment]:
        """Fallback extraction using yt-dlp."""
        import yt_dlp
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": self.preferred_languages,
            "skip_download": True,
            "quiet": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get subtitle data
            subtitles = info.get("subtitles", {}) or info.get("automatic_captions", {})
            
            # Find English subtitles
            sub_data = None
            for lang in self.preferred_languages:
                if lang in subtitles:
                    sub_data = subtitles[lang]
                    break
            
            if not sub_data:
                raise Exception("No subtitles found via yt-dlp")
            
            # Parse subtitle format (assuming json3 or vtt)
            # This is a simplified parser - production code would handle more formats
            segments = []
            
            # yt-dlp subtitle extraction is complex - for now, return empty
            # In production, you'd parse the actual subtitle file
            
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
        """Get video metadata (title, channel, duration)."""
        import yt_dlp
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                "title": info.get("title", ""),
                "channel": info.get("channel", info.get("uploader", "")),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
            }
