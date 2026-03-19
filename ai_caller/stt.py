"""Deepgram real-time STT wrapper."""
import asyncio
import json
import websockets
import config

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramSTT:
    """Manages a real-time Deepgram WebSocket connection for streaming STT."""
    
    def __init__(self, on_transcript, on_speech_started=None, sample_rate=8000):
        self.on_transcript = on_transcript          # async callback(text, is_final)
        self.on_speech_started = on_speech_started  # async callback() - for barge-in
        self.sample_rate = sample_rate
        self.ws = None
        self._receive_task = None
        self._is_speaking = False
    
    async def connect(self, encoding="mulaw"):
        """Open WebSocket connection to Deepgram."""
        params = (
            f"?encoding={encoding}"
            f"&sample_rate={self.sample_rate}"
            f"&channels=1"
            f"&model=nova-3"
            f"&punctuate=true"
            f"&endpointing=300"        # 300ms silence = end of speech
            f"&interim_results=true"
            f"&utterance_end_ms=1500"
            f"&vad_events=true"
            f"&smart_format=true"
        )
        headers = {"Authorization": f"Token {config.DEEPGRAM_API_KEY}"}
        
        self.ws = await websockets.connect(
            DEEPGRAM_WS_URL + params,
            extra_headers=headers,
            ping_interval=5,
            ping_timeout=20,
        )
        self._receive_task = asyncio.create_task(self._receive_loop())
        print(f"[STT] Connected to Deepgram ({encoding} {self.sample_rate}Hz)")

    async def connect_raw(self):
        """Connect with linear16 PCM encoding (for browser audio)."""
        await self.connect(encoding="linear16")
    
    async def send_audio(self, audio_bytes: bytes):
        """Send raw audio bytes (μ-law 8kHz) to Deepgram."""
        if self.ws and self.ws.open:
            try:
                await self.ws.send(audio_bytes)
            except Exception:
                pass
    
    async def close(self):
        """Close the STT connection."""
        if self._receive_task:
            self._receive_task.cancel()
        if self.ws:
            try:
                # Send close message
                await self.ws.send(json.dumps({"type": "CloseStream"}))
                await self.ws.close()
            except Exception:
                pass
        print("[STT] Disconnected from Deepgram")
    
    async def _receive_loop(self):
        """Receive and process transcription results from Deepgram."""
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                msg_type = data.get("type", "")
                
                if msg_type == "SpeechStarted":
                    if not self._is_speaking:
                        self._is_speaking = True
                        if self.on_speech_started:
                            await self.on_speech_started()
                
                elif msg_type == "Results":
                    is_final = data.get("is_final", False)
                    speech_final = data.get("speech_final", False)
                    
                    alt = data.get("channel", {}).get("alternatives", [{}])[0]
                    text = alt.get("transcript", "").strip()
                    
                    if text:
                        await self.on_transcript(text, is_final or speech_final)
                    
                    if is_final or speech_final:
                        self._is_speaking = False
                
                elif msg_type == "UtteranceEnd":
                    self._is_speaking = False
                    
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            print("[STT] Connection closed")
        except Exception as e:
            print(f"[STT] Receive error: {e}")
