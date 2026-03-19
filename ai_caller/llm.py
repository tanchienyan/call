"""LLM streaming wrapper using OpenAI GPT-4o."""
import asyncio
from openai import AsyncOpenAI
import config

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def stream_chat(messages: list[dict], on_text_chunk):
    """Stream LLM response. Calls on_text_chunk(text) for each chunk.
    Returns the full response text."""
    full_text = ""
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            temperature=1.0,
            max_tokens=300,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_text += delta.content
                await on_text_chunk(delta.content)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[LLM] Error: {e}")
    return full_text
