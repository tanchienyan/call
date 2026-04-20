"""Core call pipeline: manages a single call session tying STT → LLM → TTS → Twilio."""
import asyncio
import json
import time
from datetime import datetime

from stt import DeepgramSTT
from tts import stream_tts
from llm import stream_chat
from audio_utils import encode_twilio_audio, decode_twilio_audio
import storage
import copilot as copilot_mod


class CallSession:
    """Manages the full audio pipeline for one phone call."""
    
    def __init__(self, call_id: str, twilio_ws, agent_config: dict):
        self.call_id = call_id
        self.twilio_ws = twilio_ws
        self.agent_config = agent_config
        self.stream_sid = None
        
        # Conversation state
        self.messages = [{"role": "system", "content": agent_config["system_prompt"]}]
        self.transcript = []
        self.is_speaking = False           # TTS currently playing
        self.current_tts_task = None       # Active TTS generation task
        self.current_llm_task = None       # Active LLM generation task
        self.user_text_buffer = ""         # Accumulates interim STT results
        
        # STT — language from agent config, defaults to English.
        # Use "multi" for code-switched agents (Malay+English in same call).
        self.language = agent_config.get("language", "en")
        self.stt = DeepgramSTT(
            on_transcript=self._on_stt_transcript,
            on_speech_started=self._on_speech_started,
            sample_rate=8000,
            language=self.language,
        )

        # Copilot attachment for phone calls too (same bus design)
        self.copilot = copilot_mod.attach_copilot(
            call_id,
            coaching_pack_id=agent_config.get("coaching_rules"),
            compliance_pack_id=agent_config.get("compliance_pack"),
        )
        
        # Timing
        self.started_at = None
        self.last_activity = time.time()
    
    async def start(self):
        """Initialize the call session."""
        self.started_at = datetime.utcnow()
        await self.stt.connect()
        storage.update_call(self.call_id, status="connected",
                           started_at=self.started_at.isoformat())
        
        # Send first message if configured
        first_msg = self.agent_config.get("first_message", "")
        if first_msg:
            asyncio.create_task(self._speak(first_msg, record_as="agent"))
    
    async def handle_twilio_message(self, message: dict):
        """Process a message from the Twilio WebSocket."""
        event = message.get("event")
        
        if event == "start":
            self.stream_sid = message["start"]["streamSid"]
            print(f"[CALL {self.call_id}] Twilio stream started: {self.stream_sid}")
        
        elif event == "media":
            # Forward audio to Deepgram STT
            payload = message["media"]["payload"]
            audio_bytes = __import__("base64").b64decode(payload)
            await self.stt.send_audio(audio_bytes)
            self.last_activity = time.time()
        
        elif event == "stop":
            print(f"[CALL {self.call_id}] Twilio stream stopped")
            await self.stop()
    
    async def _on_speech_started(self):
        """Called when Deepgram detects the user started speaking (barge-in)."""
        if self.is_speaking:
            print(f"[CALL {self.call_id}] Barge-in detected — stopping TTS")
            await self._stop_speaking()
    
    async def _on_stt_transcript(self, text: str, is_final: bool):
        """Called when Deepgram produces a transcript."""
        if is_final and text:
            print(f"[CALL {self.call_id}] User: {text}")
            self.user_text_buffer = ""
            
            # Record transcript
            self.transcript.append({"role": "user", "text": text})
            storage.append_transcript(self.call_id, "user", text)
            self.copilot.on_turn("user", text)
            
            # Add to conversation and generate response
            self.messages.append({"role": "user", "content": text})
            asyncio.create_task(self._generate_response())
        else:
            # Interim result — accumulate for barge-in detection
            self.user_text_buffer = text
    
    async def _generate_response(self):
        """Generate LLM response and speak it."""
        # Cancel any ongoing generation
        if self.current_llm_task and not self.current_llm_task.done():
            self.current_llm_task.cancel()
        
        # Collect full LLM response via streaming, then send to TTS in sentence chunks
        full_response = ""
        sentence_buffer = ""
        sentence_ends = {'.', '!', '?'}
        tts_tasks = []
        
        async def on_text_chunk(chunk: str):
            nonlocal full_response, sentence_buffer, tts_tasks
            full_response += chunk
            sentence_buffer += chunk
            
            # Check for sentence boundary
            for i in range(len(sentence_buffer) - 1, -1, -1):
                if sentence_buffer[i] in sentence_ends and len(sentence_buffer[:i+1].strip()) > 15:
                    sentence = sentence_buffer[:i+1].strip()
                    sentence_buffer = sentence_buffer[i+1:]
                    # Speak this sentence (don't await — let it pipeline)
                    task = asyncio.create_task(self._speak(sentence))
                    tts_tasks.append(task)
                    break
        
        self.current_llm_task = asyncio.create_task(
            stream_chat(self.messages, on_text_chunk)
        )
        
        try:
            await self.current_llm_task
        except asyncio.CancelledError:
            return
        
        # Flush remaining text
        if sentence_buffer.strip():
            task = asyncio.create_task(self._speak(sentence_buffer.strip()))
            tts_tasks.append(task)
        
        # Wait for all TTS to finish
        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
        
        # Record full response
        if full_response:
            print(f"[CALL {self.call_id}] Agent: {full_response}")
            self.transcript.append({"role": "agent", "text": full_response})
            storage.append_transcript(self.call_id, "agent", full_response)
            self.messages.append({"role": "assistant", "content": full_response})
            self.copilot.on_turn("agent", full_response)
    
    async def _speak(self, text: str, record_as: str = None):
        """Convert text to speech and send audio to Twilio."""
        if not text.strip():
            return
        
        self.is_speaking = True
        voice_id = self.agent_config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
        
        async def on_audio_chunk(pcm_24k: bytes):
            """Send PCM audio to Twilio as μ-law."""
            if not self.is_speaking:
                raise asyncio.CancelledError()
            
            b64_mulaw = encode_twilio_audio(pcm_24k)
            if self.stream_sid and self.twilio_ws:
                msg = {
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": b64_mulaw}
                }
                try:
                    await self.twilio_ws.send_json(msg)
                except Exception:
                    pass
        
        try:
            vs = self.agent_config.get("voice_settings", {})
            self.current_tts_task = asyncio.create_task(
                stream_tts(text, voice_id, on_audio_chunk,
                           voice_settings=vs, language=self.language)
            )
            await self.current_tts_task
        except asyncio.CancelledError:
            pass
        finally:
            self.is_speaking = False
        
        if record_as:
            self.transcript.append({"role": record_as, "text": text})
            storage.append_transcript(self.call_id, record_as, text)
            self.messages.append({"role": "assistant", "content": text})
    
    async def _stop_speaking(self):
        """Stop current TTS playback (barge-in)."""
        self.is_speaking = False
        
        # Cancel TTS task
        if self.current_tts_task and not self.current_tts_task.done():
            self.current_tts_task.cancel()
        
        # Cancel LLM task
        if self.current_llm_task and not self.current_llm_task.done():
            self.current_llm_task.cancel()
        
        # Clear Twilio audio buffer
        if self.stream_sid and self.twilio_ws:
            try:
                await self.twilio_ws.send_json({
                    "event": "clear",
                    "streamSid": self.stream_sid,
                })
            except Exception:
                pass
    
    async def stop(self):
        """End the call session and clean up."""
        await self._stop_speaking()
        await self.stt.close()
        
        duration = 0
        if self.started_at:
            duration = (datetime.utcnow() - self.started_at).total_seconds()
        
        storage.update_call(
            self.call_id,
            status="completed",
            duration_seconds=round(duration, 1),
            transcript=self.transcript,
            ended_at=datetime.utcnow().isoformat(),
        )
        print(f"[CALL {self.call_id}] Ended. Duration: {duration:.0f}s")

        # Deferred compliance audit (LLM-based rules) — don't block teardown
        try:
            asyncio.create_task(self.copilot.finalize())
        except Exception as e:
            print(f"[CALL {self.call_id}] Copilot finalize error: {e}")
