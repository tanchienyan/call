"""ElevenLabs streaming TTS wrapper with connection pooling."""
import asyncio
import httpx
import config

ELEVENLABS_API = "https://api.elevenlabs.io/v1"

# Pre-warmed connection pool — avoids 300ms cold start per TTS call
_tts_pool: httpx.AsyncClient | None = None


def _get_pool() -> httpx.AsyncClient:
    global _tts_pool
    if _tts_pool is None:
        _tts_pool = httpx.AsyncClient(
            timeout=30,
            http2=True,  # HTTP/2 multiplexing for parallel requests
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=3),
        )
    return _tts_pool


async def stream_tts(text: str, voice_id: str, on_audio_chunk, **kwargs):
    """Stream TTS audio from ElevenLabs with pre-warmed connection pool.
    Calls on_audio_chunk(pcm_bytes) for each audio chunk.
    """
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    custom = kwargs.get("voice_settings", {})
    payload = {
        "text": text,
        "model_id": custom.get("model_id", "eleven_flash_v2_5"),
        "voice_settings": {
            "stability": custom.get("stability", 0.12),
            "similarity_boost": custom.get("similarity_boost", 0.55),
            "style": custom.get("style", 0.18),
            "use_speaker_boost": True,
        },
    }
    output_format = kwargs.get("output_format", "pcm_24000")
    url = f"{ELEVENLABS_API}/text-to-speech/{voice_id}/stream?output_format={output_format}"

    try:
        client = _get_pool()
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                error = await resp.aread()
                print(f"[TTS] Error {resp.status_code}: {error[:200]}")
                return
            async for chunk in resp.aiter_bytes(chunk_size=4800):  # 100ms of 24kHz 16-bit
                await on_audio_chunk(chunk)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[TTS] Error: {e}")


async def stream_tts_chunked(text_queue: asyncio.Queue, voice_id: str, on_audio_chunk):
    """Process text chunks from a queue and stream TTS for each sentence.
    Accumulates text until a sentence boundary, then sends to TTS.
    """
    buffer = ""
    sentence_ends = {'.', '!', '?', ':', ';'}
    
    while True:
        try:
            chunk = await asyncio.wait_for(text_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            # Flush remaining buffer
            if buffer.strip():
                await stream_tts(buffer.strip(), voice_id, on_audio_chunk)
                buffer = ""
            continue
        
        if chunk is None:  # Sentinel: LLM done
            if buffer.strip():
                await stream_tts(buffer.strip(), voice_id, on_audio_chunk)
            break
        
        buffer += chunk
        
        # Check for sentence boundaries to send in chunks
        last_boundary = -1
        for i, c in enumerate(buffer):
            if c in sentence_ends and i > 10:  # Minimum chunk size
                last_boundary = i
        
        if last_boundary > 0:
            sentence = buffer[:last_boundary + 1].strip()
            buffer = buffer[last_boundary + 1:]
            if sentence:
                await stream_tts(sentence, voice_id, on_audio_chunk)


async def list_voices() -> list[dict]:
    """List available ElevenLabs voices."""
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{ELEVENLABS_API}/voices", headers=headers)
        data = resp.json()
        voices = []
        for v in data.get("voices", []):
            voices.append({
                "voice_id": v["voice_id"],
                "name": v["name"],
                "category": v.get("category", ""),
                "labels": v.get("labels", {}),
                "preview_url": v.get("preview_url", ""),
            })
        return voices
