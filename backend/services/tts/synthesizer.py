"""
Text-to-Speech service for audio explanations.
Supports ElevenLabs, OpenAI TTS, and Edge TTS (free fallback).
"""

from typing import Tuple, Optional
import aiohttp
import hashlib
import os
import asyncio

from config.settings import settings


# Global TTS instance
_tts_service = None


def get_tts_service() -> "TTSService":
    """Get or create the global TTS instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


class TTSService:
    """
    Text-to-Speech service for generating audio explanations.
    
    Providers:
    1. ElevenLabs (default, best quality)
       - Natural, expressive voices
       - ~$0.15/1K chars
       - "eleven_turbo_v2" for low latency
       
    2. OpenAI TTS
       - Good quality, consistent
       - ~$0.015/1K chars
       - "tts-1" for speed, "tts-1-hd" for quality
       
    3. Edge TTS (fallback, free)
       - Microsoft Edge voices
       - Free, decent quality
       - Good for development/testing
    
    Voice Selection:
    - Calm, professional tutor voice
    - Clear articulation
    - Neutral accent
    - Not robotic
    """
    
    def __init__(
        self,
        provider: str = None,
        storage_path: str = None,
    ):
        self.provider = provider or settings.TTS_PROVIDER
        self.storage_path = storage_path or settings.AUDIO_STORAGE_DIR
        
        # Create storage directory
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Voice configurations
        self.voices = {
            "elevenlabs": {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # "Rachel" - calm, clear
                "model": "eleven_turbo_v2",
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
            "openai": {
                "voice": "nova",  # Warm, conversational
                "model": "tts-1",  # Fast
            },
            "edge": {
                "voice": "en-US-JennyNeural",  # Clear, professional
            },
        }
        
        # Cache for audio files
        self._audio_cache = {}
    
    async def synthesize(
        self,
        text: str,
        video_id: str,
        timestamp: float,
    ) -> Optional[Tuple[str, float]]:
        """
        Generate audio from text.
        
        Args:
            text: Text to synthesize (should be speech-friendly)
            video_id: YouTube video ID (for cache key)
            timestamp: Timestamp (for cache key)
            
        Returns:
            Tuple of (audio_url, duration_seconds) or None on failure
        """
        
        if not text or not text.strip():
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached = self._check_cache(cache_key)
        if cached:
            return cached
        
        # Generate audio based on provider
        try:
            if self.provider == "elevenlabs":
                audio_bytes = await self._elevenlabs_tts(text)
            elif self.provider == "openai":
                audio_bytes = await self._openai_tts(text)
            elif self.provider == "edge":
                audio_bytes = await self._edge_tts(text)
            else:
                print(f"Unknown TTS provider: {self.provider}")
                return None
            
            if not audio_bytes:
                return None
            
            # Save audio file
            filename = f"{video_id}_{int(timestamp)}_{cache_key[:8]}.mp3"
            filepath = os.path.join(self.storage_path, filename)
            
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            
            # Estimate duration (rough: ~150 words/minute, ~5 chars/word)
            word_count = len(text.split())
            duration = (word_count / 150) * 60
            
            # Build URL
            audio_url = f"/api/audio/{filename}"
            
            # Cache result
            self._audio_cache[cache_key] = (audio_url, duration)
            
            return audio_url, duration
            
        except Exception as e:
            print(f"TTS synthesis error: {e}")
            return None
    
    async def _elevenlabs_tts(self, text: str) -> Optional[bytes]:
        """Generate audio using ElevenLabs API."""
        
        api_key = settings.ELEVENLABS_API_KEY
        if not api_key:
            print("ElevenLabs API key not configured")
            return None
        
        config = self.voices["elevenlabs"]
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{config['voice_id']}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": config["model"],
                    "voice_settings": {
                        "stability": config["stability"],
                        "similarity_boost": config["similarity_boost"],
                        "style": 0.0,  # Natural, not dramatic
                        "use_speaker_boost": True,
                    },
                },
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    error = await resp.text()
                    print(f"ElevenLabs error: {resp.status} - {error}")
                    return None
    
    async def _openai_tts(self, text: str) -> Optional[bytes]:
        """Generate audio using OpenAI TTS API."""
        
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            print("OpenAI API key not configured")
            return None
        
        config = self.voices["openai"]
        url = "https://api.openai.com/v1/audio/speech"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config["model"],
                    "voice": config["voice"],
                    "input": text,
                    "response_format": "mp3",
                },
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    error = await resp.text()
                    print(f"OpenAI TTS error: {resp.status} - {error}")
                    return None
    
    async def _edge_tts(self, text: str) -> Optional[bytes]:
        """Generate audio using Edge TTS (free, local)."""
        
        try:
            import edge_tts
        except ImportError:
            print("edge-tts not installed")
            return None
        
        config = self.voices["edge"]
        
        try:
            communicate = edge_tts.Communicate(text, config["voice"])
            
            # Edge TTS returns chunks, collect them all
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            if audio_chunks:
                return b"".join(audio_chunks)
            return None
            
        except Exception as e:
            print(f"Edge TTS error: {e}")
            return None
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key from text content."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Tuple[str, float]]:
        """Check if audio is cached."""
        if cache_key in self._audio_cache:
            url, duration = self._audio_cache[cache_key]
            # Verify file still exists
            filename = url.split("/")[-1]
            filepath = os.path.join(self.storage_path, filename)
            if os.path.exists(filepath):
                return url, duration
        return None
    
    def list_available_voices(self) -> dict:
        """List available voices for each provider."""
        return {
            "elevenlabs": [
                {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "style": "Calm, clear"},
                {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "style": "Warm, friendly"},
                {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "style": "Young, enthusiastic"},
            ],
            "openai": [
                {"id": "nova", "name": "Nova", "style": "Warm, conversational"},
                {"id": "alloy", "name": "Alloy", "style": "Neutral, balanced"},
                {"id": "shimmer", "name": "Shimmer", "style": "Expressive, bright"},
            ],
            "edge": [
                {"id": "en-US-JennyNeural", "name": "Jenny", "style": "Professional"},
                {"id": "en-US-GuyNeural", "name": "Guy", "style": "Friendly male"},
                {"id": "en-GB-SoniaNeural", "name": "Sonia", "style": "British female"},
            ],
        }
