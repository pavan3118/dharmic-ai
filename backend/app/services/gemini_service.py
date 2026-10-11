import os
import asyncio
import time
from typing import AsyncGenerator, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.app.core.config import settings


class GeminiService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)

        # Model names can be overridden from .env without touching code.
        # If a name is rejected (404), run client.models.list() to see valid ones,
        # or use the alias "gemini-flash-latest".
        self.primary_model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash")
        self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")

    @staticmethod
    def _should_wait(error: APIError) -> bool:
        """Only back off for rate limits / temporary server issues."""
        return getattr(error, "code", None) in (429, 500, 502, 503, 504)

    def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        retries: int = 3,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        last_error: Optional[Exception] = None
        for attempt in range(retries):
            model_to_use = self.primary_model if attempt == 0 else self.fallback_model
            try:
                response = self.client.models.generate_content(
                    model=model_to_use,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except APIError as e:
                last_error = e
                print(f"[gemini] {model_to_use} failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1 and self._should_wait(e):
                    time.sleep(2 * (attempt + 1))

        raise last_error

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        last_error: Optional[Exception] = None
        for model in (self.primary_model, self.fallback_model):
            started = False
            try:
                # Async client: does not block the FastAPI event loop.
                stream = await self.client.aio.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                async for chunk in stream:
                    if chunk.text:
                        started = True
                        yield chunk.text
                return
            except APIError as e:
                last_error = e
                print(f"[gemini] stream with {model} failed: {e}")
                if started:
                    # Text was already sent to the user; can't switch models mid-answer.
                    raise
                if self._should_wait(e):
                    await asyncio.sleep(2)

        raise last_error


gemini_service = GeminiService()