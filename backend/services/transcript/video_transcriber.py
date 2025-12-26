"""
Video upload and transcription service.
Extracts audio from video and transcribes using Bytez or OpenAI Whisper.
"""

import os
import tempfile
import uuid
from typing import Optional
from pathlib import Path

from models.transcript import VideoTranscript, RawSegment
from config.settings import settings


class VideoTranscriber:
    """
    Handles video file uploads and transcription.
    
    Flow:
    1. Save uploaded video to temp file
    2. Extract audio using moviepy/ffmpeg
    3. Transcribe audio using Bytez or Whisper
    4. Convert to RawSegments
    """
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.transcription_provider = os.getenv("TRANSCRIPTION_PROVIDER", "openai")  # "openai" or "bytez"
        self.bytez_api_key = os.getenv("BYTEZ_API_KEY", "")
        self.bytez_model_id = os.getenv("BYTEZ_MODEL_ID", "openai/whisper-large-v3")
    
    async def transcribe_video(
        self,
        video_content: bytes,
        filename: str,
        video_id: Optional[str] = None
    ) -> VideoTranscript:
        """
        Transcribe a video file.
        
        Args:
            video_content: Raw video file bytes
            filename: Original filename
            video_id: Optional custom ID
            
        Returns:
            VideoTranscript with transcribed segments
        """
        if not video_id:
            video_id = f"video_{uuid.uuid4().hex[:11]}"
        
        transcript = VideoTranscript(
            video_id=video_id,
            source="video_upload",
        )
        
        try:
            # Save video to temp file
            video_path = await self._save_temp_file(video_content, filename)
            
            # Extract audio
            audio_path = await self._extract_audio(video_path)
            
            # Transcribe
            if self.transcription_provider == "bytez" and self.bytez_api_key:
                segments = await self._transcribe_bytez(audio_path)
            else:
                segments = await self._transcribe_openai(audio_path)
            
            transcript.segments = segments
            transcript.status = "ready"
            
            # Calculate duration
            if segments:
                last = segments[-1]
                transcript.duration = last.start + last.duration
            
            # Cleanup temp files
            self._cleanup_temp_files(video_path, audio_path)
            
        except Exception as e:
            transcript.status = "error"
            transcript.error_message = f"Transcription failed: {str(e)}"
        
        return transcript
    
    async def _save_temp_file(self, content: bytes, filename: str) -> str:
        """Save uploaded content to temp file."""
        ext = Path(filename).suffix or ".mp4"
        temp_path = os.path.join(self.temp_dir, f"video_{uuid.uuid4().hex}{ext}")
        
        with open(temp_path, "wb") as f:
            f.write(content)
        
        return temp_path
    
    async def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video file."""
        audio_path = video_path.rsplit(".", 1)[0] + ".mp3"
        
        try:
            # Try using moviepy
            from moviepy.editor import VideoFileClip
            
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video.close()
            
        except ImportError:
            # Fallback to ffmpeg command
            import subprocess
            
            result = subprocess.run([
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                "-y", audio_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg error: {result.stderr}")
        
        return audio_path
    
    async def _transcribe_openai(self, audio_path: str) -> list[RawSegment]:
        """Transcribe using OpenAI Whisper API."""
        import openai
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        with open(audio_path, "rb") as audio_file:
            # Use verbose_json to get timestamps
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        segments = []
        
        # Handle response format
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                segments.append(RawSegment(
                    text=seg.get('text', '').strip(),
                    start=seg.get('start', 0),
                    duration=seg.get('end', 0) - seg.get('start', 0)
                ))
        elif hasattr(response, 'text'):
            # Fallback: single segment with full text
            segments.append(RawSegment(
                text=response.text.strip(),
                start=0,
                duration=0
            ))
        
        return segments
    
    async def _transcribe_bytez(self, audio_path: str) -> list[RawSegment]:
        """Transcribe using Bytez platform."""
        try:
            from langchain_bytez import BytezChatModel
            from langchain.schema import HumanMessage, SystemMessage
            
            # Upload audio to get URL (Bytez requires URL)
            # For now, we'll use a workaround by reading the file
            # In production, you'd upload to cloud storage first
            
            import base64
            with open(audio_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode()
            
            bytez_model = BytezChatModel(
                model_id=self.bytez_model_id,
                api_key=self.bytez_api_key,
                capacity={"min": 1, "max": 1},
                params={"max_new_tokens": 4096},
            )
            
            system_message = SystemMessage(
                content=[
                    {"type": "text", "text": "You are a transcription assistant. Transcribe the audio accurately with timestamps in format [MM:SS]."},
                ]
            )
            
            human_message = HumanMessage(
                content=[
                    {"type": "text", "text": "Transcribe this audio with timestamps."},
                    {"type": "audio", "data": audio_base64, "format": "mp3"},
                ]
            )
            
            response = bytez_model.invoke([system_message, human_message])
            
            # Parse the response into segments
            segments = self._parse_timestamped_text(response.content)
            
            return segments
            
        except ImportError:
            raise Exception("langchain_bytez not installed. Install with: pip install langchain-bytez")
        except Exception as e:
            raise Exception(f"Bytez transcription failed: {str(e)}")
    
    def _parse_timestamped_text(self, text: str) -> list[RawSegment]:
        """Parse text with [MM:SS] timestamps into segments."""
        import re
        
        segments = []
        
        # Pattern: [00:00] or [0:00] followed by text
        pattern = r'\[(\d{1,2}):(\d{2})\]\s*(.+?)(?=\[\d{1,2}:\d{2}\]|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for i, (mins, secs, segment_text) in enumerate(matches):
            start = int(mins) * 60 + int(secs)
            
            # Calculate duration from next segment
            if i < len(matches) - 1:
                next_mins, next_secs, _ = matches[i + 1]
                next_start = int(next_mins) * 60 + int(next_secs)
                duration = next_start - start
            else:
                duration = 30  # Default duration for last segment
            
            segments.append(RawSegment(
                text=segment_text.strip(),
                start=float(start),
                duration=float(duration)
            ))
        
        # If no timestamps found, create single segment
        if not segments and text.strip():
            segments.append(RawSegment(
                text=text.strip(),
                start=0,
                duration=0
            ))
        
        return segments
    
    def _cleanup_temp_files(self, *paths):
        """Remove temporary files."""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except:
                pass


def create_transcript_from_video(
    video_id: str,
    segments: list[RawSegment],
    title: str = ""
) -> VideoTranscript:
    """Create VideoTranscript from transcribed segments."""
    transcript = VideoTranscript(
        video_id=video_id,
        source="video_upload",
        status="ready" if segments else "error",
        segments=segments,
        title=title,
    )
    
    if segments:
        last = segments[-1]
        transcript.duration = last.start + last.duration
    else:
        transcript.error_message = "No segments transcribed from video"
    
    return transcript
