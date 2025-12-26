"""
Prompt templates for the AI tutor.

Design principles:
1. ZERO prior knowledge assumption
2. Define ALL technical terms
3. Use analogies and real-world examples
4. Follow video's teaching flow
5. Never hallucinate beyond provided context
"""

from typing import List
from models.explanation import ExplanationChunk


class TutorPrompts:
    """
    Prompt templates for the AI tutor.
    
    The prompts are designed to:
    - Force the LLM to stay within retrieved context
    - Generate beginner-friendly explanations
    - Follow a consistent structure
    - Be suitable for both text and audio output
    """
    
    SYSTEM_PROMPT = """You are a patient, expert AI tutor helping a student understand a YouTube video.

## Your Teaching Style
- Assume the student has ZERO prior knowledge of this topic
- Define EVERY technical term before using it
- Use simple, conversational language (8th grade reading level)
- Give real-world analogies for abstract concepts
- Build understanding step-by-step
- Be encouraging and supportive

## Critical Rules
1. ONLY explain concepts from the provided transcript context
2. If information isn't in the context, say "The video doesn't cover this, but..." and briefly explain
3. Follow the video's teaching order - don't jump ahead
4. Keep explanations focused on the timestamp the student paused at
5. Format explanations with clear structure

## Response Format
Always structure your response as:

### 🎯 What's Being Discussed
[1-2 sentence summary of the concept at this timestamp]

### 📖 Simple Explanation
[Clear explanation with definitions and analogies. Break down complex ideas into digestible parts.]

### 🔗 How It Connects
[How this relates to what was covered earlier in the video]

### 💡 Key Takeaway
[One memorable sentence summarizing the main idea]

## Example Analogies to Use
- "Think of it like..." followed by an everyday comparison
- "Imagine you're..." followed by a relatable scenario
- "It's similar to how..." followed by something familiar

Remember: Your goal is to make the student say "Oh, NOW I get it!" after reading your explanation."""

    @staticmethod
    def build_explanation_prompt(
        chunks: List[ExplanationChunk],
        timestamp: float,
        user_query: str = None,
    ) -> str:
        """
        Build the user prompt with retrieved context.
        
        Organizes chunks by relevance type to give the LLM
        clear context about what's being discussed now vs.
        what was explained earlier.
        """
        
        # Separate chunks by type
        temporal = [c for c in chunks if c.relevance_type == "temporal"]
        foundational = [c for c in chunks if c.relevance_type == "foundational"]
        semantic = [c for c in chunks if c.relevance_type == "semantic"]
        
        # Default query if none provided
        if not user_query:
            user_query = "I don't understand this"
        
        prompt = f"""## Student's Question
The student paused the video at timestamp {TutorPrompts._format_time(timestamp)}.
They said: "{user_query}"

## Video Transcript Context

### 📍 Currently Being Discussed (around {TutorPrompts._format_time(timestamp)})
This is what the video is explaining right now:
"""
        
        if temporal:
            for chunk in temporal:
                time_range = f"[{TutorPrompts._format_time(chunk.start_time)} → {TutorPrompts._format_time(chunk.end_time)}]"
                prompt += f"\n{time_range}\n\"{chunk.text}\"\n"
        else:
            prompt += "\n[No transcript available for this exact moment]\n"
        
        if foundational:
            prompt += "\n### 📚 Earlier Definitions & Foundations\n"
            prompt += "The video explained these concepts earlier:\n"
            for chunk in foundational:
                time_str = f"[{TutorPrompts._format_time(chunk.start_time)}]"
                prompt += f"\n{time_str}\n\"{chunk.text}\"\n"
        
        if semantic:
            prompt += "\n### 🔗 Related Concepts from This Video\n"
            prompt += "These parts of the video discuss similar ideas:\n"
            for chunk in semantic:
                time_str = f"[{TutorPrompts._format_time(chunk.start_time)}]"
                prompt += f"\n{time_str}\n\"{chunk.text}\"\n"
        
        prompt += """
---

## Your Task
Based on the transcript context above, explain what's happening at this point in the video.

Remember:
✓ Define all technical terms in simple words
✓ Use everyday analogies to explain abstract concepts
✓ Build on what was explained earlier in the video
✓ Keep your explanation focused and clear
✓ Only use information from the transcript above
✗ Don't make up information not in the context
✗ Don't assume the student knows anything about this topic"""
        
        return prompt
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    # For TTS: Generate speaking-friendly version
    AUDIO_SIMPLIFICATION_PROMPT = """Convert the following explanation into natural spoken text that sounds like a calm, friendly tutor speaking directly to a student.

Rules:
- Remove all markdown formatting (###, **, bullets, etc.)
- Remove emoji symbols (🎯, 📖, 🔗, 💡 etc.)
- Convert any lists into flowing sentences
- Make it sound conversational and warm
- Use transitional phrases like "So,", "Now,", "The key thing here is...", "Let me explain..."
- Address the student directly using "you" and "your"
- Keep the same content and meaning
- Aim for about 30-45 seconds of speech (roughly 100-140 words)

Original explanation:
{explanation}

Spoken version (natural, conversational):"""
    
    @staticmethod
    def build_followup_prompt(
        previous_explanation: str,
        followup_question: str,
        chunks: List[ExplanationChunk],
    ) -> str:
        """
        Build a prompt for follow-up questions.
        Maintains context from the previous explanation.
        """
        
        prompt = f"""## Previous Explanation
You previously explained this to the student:
---
{previous_explanation}
---

## Follow-up Question
The student now asks: "{followup_question}"

## Additional Context from Video
"""
        
        for chunk in chunks:
            time_str = f"[{TutorPrompts._format_time(chunk.start_time)}]"
            prompt += f"\n{time_str}\n\"{chunk.text}\"\n"
        
        prompt += """
---

Answer the follow-up question while:
- Building on your previous explanation
- Staying within the video's context
- Using the same simple, encouraging teaching style
- Defining any new terms introduced"""
        
        return prompt


# Additional prompt templates for specific scenarios

DEFINITION_PROMPT = """Based on this video transcript context, provide a simple definition for the term "{term}".

Context:
{context}

Your definition should:
1. Be understandable to someone with no background in this topic
2. Use an everyday analogy
3. Be 2-3 sentences maximum
4. Only use information from the context provided"""


SUMMARY_PROMPT = """Summarize the key concepts discussed in this video section in 2-3 sentences.

Transcript:
{context}

Requirements:
- Focus on the main ideas, not details
- Use simple language
- Don't introduce concepts not mentioned in the transcript"""
