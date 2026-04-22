"""LLM streaming wrapper using OpenAI GPT-4o."""
import asyncio
import random

from openai import AsyncOpenAI, RateLimitError, APIError

import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# Live-call default. Enough for a ~300-character agent turn with natural
# phrasing — bumping this globally hurts latency. Non-realtime callers (QA,
# synth, compliance LLM audit) pass a larger value explicitly.
DEFAULT_MAX_TOKENS = 300


async def stream_chat(
    messages: list[dict],
    on_text_chunk,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 1.0,
    max_retries: int = 4,
):
    """Stream LLM response. Calls ``on_text_chunk(text)`` for each chunk.

    Returns the full response text.

    Retries on OpenAI rate limits and transient API errors with exponential
    backoff + jitter. The real-time pipeline calls this with the default
    ``max_tokens`` (keeps turns short + latency low). Non-realtime callers
    (QA engine, synth data, compliance LLM audit) should pass a larger
    ``max_tokens`` explicitly — otherwise long JSON responses get truncated
    and fail downstream ``json.loads`` parsing.
    """
    full_text = ""
    attempt = 0
    while True:
        try:
            stream = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    await on_text_chunk(delta.content)
            return full_text
        except asyncio.CancelledError:
            return full_text
        except RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[LLM] Rate limit exhausted after {max_retries} retries: {e}")
                return full_text
            # Exponential backoff with jitter, starting at 2s (429 windows
            # on gpt-4o TPM are typically sub-second to ~20s).
            wait = min(30.0, (2 ** attempt) + random.random())
            print(f"[LLM] 429 rate limit — backing off {wait:.1f}s (attempt {attempt}/{max_retries})")
            await asyncio.sleep(wait)
            # Reset streamed output so the retry doesn't prepend partial text.
            full_text = ""
        except APIError as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[LLM] API error exhausted after {max_retries} retries: {e}")
                return full_text
            wait = min(15.0, (1.5 ** attempt) + random.random())
            print(f"[LLM] Transient API error — retrying in {wait:.1f}s ({attempt}/{max_retries})")
            await asyncio.sleep(wait)
            full_text = ""
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return full_text
