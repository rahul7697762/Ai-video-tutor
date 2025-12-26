"""
Manual transcript upload and parsing service.
Supports SRT, VTT, and plain text formats.
"""

import re
from typing import Optional
from models.transcript import VideoTranscript, RawSegment


class TranscriptParser:
    """Parse uploaded transcript files into segments."""
    
    def parse(self, content: str, format_hint: Optional[str] = None) -> list[RawSegment]:
        """
        Parse transcript content into segments.
        
        Args:
            content: Raw transcript text
            format_hint: Optional format hint ('srt', 'vtt', 'txt')
            
        Returns:
            List of RawSegment objects
        """
        # Try to detect format if not specified
        if not format_hint:
            format_hint = self._detect_format(content)
        
        if format_hint == 'srt':
            return self._parse_srt(content)
        elif format_hint == 'vtt':
            return self._parse_vtt(content)
        else:
            return self._parse_plain_text(content)
    
    def _detect_format(self, content: str) -> str:
        """Detect transcript format from content."""
        content_lower = content.strip().lower()
        
        if content_lower.startswith('webvtt'):
            return 'vtt'
        
        # SRT format: starts with "1\n00:00:00,000 --> 00:00:02,000"
        srt_pattern = r'^\d+\s*\n\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->'
        if re.search(srt_pattern, content, re.MULTILINE):
            return 'srt'
        
        # VTT format: has timestamps like "00:00:00.000 --> 00:00:02.000"
        vtt_pattern = r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->'
        if re.search(vtt_pattern, content):
            return 'vtt'
        
        return 'txt'
    
    def _parse_srt(self, content: str) -> list[RawSegment]:
        """Parse SRT format subtitle file."""
        segments = []
        
        # Split into blocks (separated by blank lines)
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            # Skip sequence number (first line)
            # Parse timestamp line
            timestamp_line = lines[1] if len(lines) > 1 else ''
            text_lines = lines[2:] if len(lines) > 2 else []
            
            # Parse timestamps: 00:00:00,000 --> 00:00:02,000
            match = re.match(
                r'(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})',
                timestamp_line
            )
            
            if match:
                start_h, start_m, start_s, start_ms = map(int, match.groups()[:4])
                end_h, end_m, end_s, end_ms = map(int, match.groups()[4:])
                
                start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
                end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
                
                text = self._clean_text(' '.join(text_lines))
                
                if text:
                    segments.append(RawSegment(
                        text=text,
                        start=start,
                        duration=end - start
                    ))
        
        return segments
    
    def _parse_vtt(self, content: str) -> list[RawSegment]:
        """Parse WebVTT format subtitle file."""
        segments = []
        
        # Remove WEBVTT header and any metadata
        lines = content.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            if '-->' in line:
                content_start = i
                break
            if line.strip().upper() == 'WEBVTT':
                continue
        
        # Process from content start
        current_block = []
        for line in lines[content_start:]:
            if line.strip():
                current_block.append(line)
            elif current_block:
                # Process block
                segment = self._parse_vtt_block(current_block)
                if segment:
                    segments.append(segment)
                current_block = []
        
        # Don't forget last block
        if current_block:
            segment = self._parse_vtt_block(current_block)
            if segment:
                segments.append(segment)
        
        return segments
    
    def _parse_vtt_block(self, lines: list[str]) -> Optional[RawSegment]:
        """Parse a single VTT cue block."""
        timestamp_line = None
        text_lines = []
        
        for line in lines:
            if '-->' in line:
                timestamp_line = line
            elif timestamp_line:
                text_lines.append(line)
        
        if not timestamp_line:
            return None
        
        # Parse: 00:00:00.000 --> 00:00:02.000
        match = re.match(
            r'(?:(\d{2}):)?(\d{2}):(\d{2})[,\.](\d{3})\s*-->\s*(?:(\d{2}):)?(\d{2}):(\d{2})[,\.](\d{3})',
            timestamp_line
        )
        
        if match:
            groups = match.groups()
            start_h = int(groups[0]) if groups[0] else 0
            start_m = int(groups[1])
            start_s = int(groups[2])
            start_ms = int(groups[3])
            
            end_h = int(groups[4]) if groups[4] else 0
            end_m = int(groups[5])
            end_s = int(groups[6])
            end_ms = int(groups[7])
            
            start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
            end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
            
            text = self._clean_text(' '.join(text_lines))
            
            if text:
                return RawSegment(
                    text=text,
                    start=start,
                    duration=end - start
                )
        
        return None
    
    def _parse_plain_text(self, content: str) -> list[RawSegment]:
        """Parse plain text into segments (one segment per paragraph or sentence)."""
        segments = []
        
        # Split by paragraphs (double newlines)
        paragraphs = re.split(r'\n\s*\n', content.strip())
        
        current_time = 0.0
        avg_reading_speed = 150  # words per minute
        
        for para in paragraphs:
            text = self._clean_text(para)
            if not text:
                continue
            
            # Estimate duration based on word count
            word_count = len(text.split())
            duration = (word_count / avg_reading_speed) * 60  # Convert to seconds
            duration = max(3.0, min(duration, 60.0))  # Clamp between 3-60 seconds
            
            segments.append(RawSegment(
                text=text,
                start=current_time,
                duration=duration
            ))
            
            current_time += duration
        
        return segments
    
    def _clean_text(self, text: str) -> str:
        """Clean transcript text."""
        # Remove HTML/VTT tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove [Music], [Applause] style markers
        text = re.sub(r'\[[^\]]+\]', '', text)
        
        # Remove speaker labels like "SPEAKER 1:" or ">> "
        text = re.sub(r'^(SPEAKER\s*\d*:|>>)\s*', '', text, flags=re.MULTILINE)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()


def create_transcript_from_upload(
    video_id: str,
    content: str,
    format_hint: Optional[str] = None,
    video_title: str = ""
) -> VideoTranscript:
    """
    Create a VideoTranscript from uploaded content.
    
    Args:
        video_id: Custom ID for the transcriptc (or YouTube video ID)
        content: Raw transcript content
        format_hint: File format ('srt', 'vtt', 'txt')
        video_title: Optional title for the video
        
    Returns:
        VideoTranscript object ready for processing
    """
    parser = TranscriptParser()
    segments = parser.parse(content, format_hint)
    
    transcript = VideoTranscript(
        video_id=video_id,
        source="manual_upload",
        status="ready" if segments else "error",
        segments=segments,
    )
    
    if segments:
        last = segments[-1]
        transcript.duration = last.start + last.duration
    else:
        transcript.error_message = "Could not parse any segments from the uploaded transcript"
    
    return transcript
