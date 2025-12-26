"""
LLM service for generating explanations.
Supports OpenAI GPT models and Anthropic Claude.
"""

from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
import anthropic

from config.settings import settings


# Global LLM instance
_tutor_llm = None


def get_tutor_llm() -> "TutorLLM":
    """Get or create the global LLM instance."""
    global _tutor_llm
    if _tutor_llm is None:
        _tutor_llm = TutorLLM()
    return _tutor_llm


class TutorLLM:
    """
    LLM service for generating tutor explanations.
    
    Supports:
    - OpenAI: gpt-4o-mini (default, cost-effective), gpt-4o (higher quality)
    - Anthropic: claude-3-haiku (fast), claude-3-sonnet (balanced)
    
    Features:
    - Streaming for lower perceived latency
    - Token usage tracking
    - Error handling with fallback responses
    """
    
    def __init__(
        self,
        provider: str = None,
        model: str = None,
    ):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        
        # Initialize clients
        if self.provider == "openai":
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            self.anthropic_client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        
        # Model-specific settings
        self.max_tokens = 1024  # Reasonable limit for explanations
        self.temperature = 0.7  # Balanced creativity/consistency
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        Generate a complete response from the LLM.
        
        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User message with context
            max_tokens: Maximum response length
            temperature: Creativity level (0-1)
            
        Returns:
            Complete generated text
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        try:
            if self.provider == "openai":
                return await self._generate_openai(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            elif self.provider == "anthropic":
                return await self._generate_anthropic(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
                
        except Exception as e:
            print(f"LLM generation error: {e}")
            return self._fallback_response(str(e))
    
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens for lower perceived latency.
        
        Yields:
            Individual tokens as they're generated
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        try:
            if self.provider == "openai":
                async for token in self._stream_openai(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    yield token
                    
            elif self.provider == "anthropic":
                async for token in self._stream_anthropic(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    yield token
                    
        except Exception as e:
            print(f"LLM streaming error: {e}")
            yield self._fallback_response(str(e))
    
    async def _generate_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate using OpenAI API."""
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    
    async def _stream_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream using OpenAI API."""
        stream = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate using Anthropic API."""
        response = await self.anthropic_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.content[0].text
    
    async def _stream_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream using Anthropic API."""
        async with self.anthropic_client.messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    def _fallback_response(self, error: str) -> str:
        """Generate a fallback response when LLM fails."""
        return f"""### ⚠️ Explanation Unavailable

I'm sorry, but I couldn't generate an explanation at this moment.

**What happened:** There was a temporary issue connecting to the AI service.

**What you can do:**
1. Try again in a few seconds
2. Rewind the video slightly and pause again
3. Check your internet connection

If the problem persists, the video transcript may not have enough context around this timestamp to generate a helpful explanation.

*Technical details: {error[:100]}...*"""
