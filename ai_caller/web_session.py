"""Browser-based voice call session — same pipeline as phone, no Twilio cost."""
import asyncio
import json
import time
import base64
import struct
from datetime import datetime

from stt import DeepgramSTT
from tts import stream_tts
from llm import stream_chat
from phone_fx import phone_effect
from smart_turn import TurnDetector
import storage


class WebCallSession:
    """Voice conversation via browser WebSocket — mirrors phone CallSession."""

    def __init__(self, call_id: str, ws, agent_config: dict):
        self.call_id = call_id
        self.ws = ws
        self.agent_config = agent_config

        self.messages = [{"role": "system", "content": agent_config["system_prompt"]}]
        self.transcript = []
        self.is_speaking = False
        self.current_tts_task = None
        self.current_llm_task = None
        self.mute_stt = False  # Mute STT while AI is speaking (echo suppression)
        self._pending_bargein = False
        self._interrupted_context = False
        self._chars_actually_played = 0
        self.chars_spoken = 0  # Track ElevenLabs character usage

        self.phone_fx = agent_config.get("phone_fx", True)  # Default ON
        self.phone_fx_settings = agent_config.get("phone_fx_settings", {
            "noise_level": 0.002, "bandpass_low": 300, "bandpass_high": 3400,
            "gain_db": -2.0, "clip_threshold": 0.65
        })
        print(f"[WEB {call_id}] phone_fx={self.phone_fx} settings={self.phone_fx_settings}", flush=True)
        
        self.turn_detector = TurnDetector()
        
        self.stt = DeepgramSTT(
            on_transcript=self._on_stt_transcript,
            on_speech_started=self._on_speech_started,
            sample_rate=16000,  # Browser sends 16kHz
        )
        self.started_at = None

    async def start(self):
        self.started_at = datetime.utcnow()
        
        # Connect Deepgram STT for browser audio (PCM 16kHz)
        self.stt.sample_rate = 16000
        try:
            await self.stt.connect_raw()
            print(f"[WEB {self.call_id}] STT connected")
        except Exception as e:
            print(f"[WEB {self.call_id}] STT connect failed: {e}")
            import traceback; traceback.print_exc()
            return
        
        storage.update_call(self.call_id, status="connected",
                           started_at=self.started_at.isoformat())

        # Generate opening line via LLM (so it varies each time)
        try:
            self.messages.append({
                "role": "user",
                "content": "[The customer just picked up the phone. Say your opening line — greet them naturally and check if you're speaking to the right person. Vary your greeting each time — don't always start the same way.]"
            })
            opening = ""
            async def collect_opening(chunk):
                nonlocal opening
                opening += chunk
            await stream_chat(self.messages, collect_opening)
            if opening:
                # Replace the fake user message with the actual opening flow
                self.messages.pop()  # Remove the instruction
                self.messages.append({"role": "assistant", "content": opening})
                await self._speak(opening, record_as="agent")
                print(f"[WEB {self.call_id}] Opening: {opening}", flush=True)
        except Exception as e:
            print(f"[WEB {self.call_id}] Opening failed: {e}", flush=True)
            import traceback; traceback.print_exc()

    async def handle_audio(self, audio_bytes: bytes):
        """Receive raw PCM 16-bit 16kHz audio from browser."""
        # Feed to Smart Turn detector (always, for analysis)
        self.turn_detector.feed_audio(audio_bytes, is_speech=not self.is_speaking)
        if not self.mute_stt:
            await self.stt.send_audio(audio_bytes)

    async def _on_speech_started(self):
        if self.is_speaking:
            # Don't immediately barge-in — wait for actual transcript
            # to distinguish backchannel ("mm-hm") from real interruption
            self._pending_bargein = True
            print(f"[WEB {self.call_id}] Speech detected during AI turn, waiting for transcript...", flush=True)

    async def _on_stt_transcript(self, text: str, is_final: bool):
        if is_final and text:
            # Check if this is a backchannel during AI speech
            BACKCHANNELS = {"mm", "mmm", "mhm", "mm-hm", "mm-hmm", "uh-huh", "uh huh",
                           "yeah", "yep", "yes", "right", "okay", "ok", "sure", "got it",
                           "ah", "oh", "hm", "hmm"}
            is_backchannel = text.strip().lower().rstrip('.!?,') in BACKCHANNELS

            if self.is_speaking and is_backchannel:
                # Backchannel — don't interrupt, just log it
                print(f"[WEB {self.call_id}] Backchannel (ignored): {text}", flush=True)
                self._pending_bargein = False
                await self._send_json({"type": "transcript", "role": "user", "text": f"({text})"})
                return

            if self.is_speaking or getattr(self, '_pending_bargein', False):
                # Real interruption — stop and note what AI was saying
                print(f"[WEB {self.call_id}] Real barge-in: {text}", flush=True)
                self._pending_bargein = False
                # Remember what AI was saying when interrupted
                self._interrupted_context = True
                await self._stop_speaking()

            # Use Smart Turn to verify user actually finished speaking
            is_complete, confidence = await self.turn_detector.is_turn_complete()
            if not is_complete and not is_backchannel:
                print(f"[WEB {self.call_id}] Smart Turn: user not done yet (conf={confidence:.2f}), waiting...", flush=True)
                await self._send_json({"type": "interim", "text": text})
                return  # Don't respond yet, wait for more speech
            
            self.turn_detector.reset()  # Reset for next turn
            
            print(f"[WEB {self.call_id}] User: {text}")
            self.transcript.append({"role": "user", "text": text})
            storage.append_transcript(self.call_id, "user", text)
            self.messages.append({"role": "user", "content": text})

            await self._send_json({"type": "transcript", "role": "user", "text": text})
            asyncio.create_task(self._generate_response())
        elif text:
            await self._send_json({"type": "interim", "text": text})

    async def _generate_response(self):
        if self.current_llm_task and not self.current_llm_task.done():
            self.current_llm_task.cancel()

        import time as _time
        t0 = _time.monotonic()

        # If we were interrupted, inject context so LLM handles it naturally
        if getattr(self, '_interrupted_context', False):
            self._interrupted_context = False
            self.messages.insert(-1, {
                "role": "system",
                "content": "[You were just interrupted mid-sentence. Acknowledge briefly — 'Sorry, go ahead' or 'Oh right —' then respond to what they said. Don't repeat what you were saying before.]"
            })

        full_response = ""
        sentence_buffer = ""
        sentence_queue = asyncio.Queue()
        import re
        # Trigger TTS at any punctuation — much faster than waiting for 15+ chars
        PUNCT = re.compile(r'[.!?,;:\-—]')

        async def on_text_chunk(chunk):
            nonlocal full_response, sentence_buffer
            full_response += chunk
            sentence_buffer += chunk

            # Find last punctuation mark — send everything up to it
            match = None
            for m in PUNCT.finditer(sentence_buffer):
                if m.start() >= 3:  # At least a few chars before punctuation
                    match = m
            if match:
                sentence = sentence_buffer[:match.end()].strip()
                sentence_buffer = sentence_buffer[match.end():]
                if sentence:
                    await sentence_queue.put(sentence)

        # Speaker task: reads sentences from queue and speaks them sequentially
        async def speaker():
            while True:
                sentence = await sentence_queue.get()
                if sentence is None:
                    break
                await self._speak(sentence)

        speaker_task = asyncio.create_task(speaker())

        # Soft timeout: if LLM takes >2.5s to produce first text, say a filler
        import random
        fillers = ["Hmm... yeah.", "Right, let me see...", "So...", "Mm-hmm...", "Got it..."]
        filler_spoken = False

        original_on_text = on_text_chunk
        llm_first_token = [False]
        async def on_text_chunk_with_filler(chunk):
            nonlocal filler_spoken
            if not llm_first_token[0]:
                llm_first_token[0] = True
                print(f"[LATENCY {self.call_id}] LLM TTFT: {(_time.monotonic()-t0)*1000:.0f}ms", flush=True)
            filler_spoken = True
            await original_on_text(chunk)

        async def soft_timeout():
            nonlocal filler_spoken
            await asyncio.sleep(2.5)
            if not filler_spoken and not sentence_queue.qsize():
                filler = random.choice(fillers)
                await self._speak(filler)

        soft_timeout_task = asyncio.create_task(soft_timeout())
        on_text_chunk = on_text_chunk_with_filler

        self.current_llm_task = asyncio.create_task(
            stream_chat(self.messages, on_text_chunk)
        )

        try:
            await self.current_llm_task
        except asyncio.CancelledError:
            soft_timeout_task.cancel()
            await sentence_queue.put(None)
            speaker_task.cancel()
            return
        
        soft_timeout_task.cancel()

        # Flush remaining text
        if sentence_buffer.strip():
            await sentence_queue.put(sentence_buffer.strip())

        # Signal speaker to stop
        await sentence_queue.put(None)
        await speaker_task

        if full_response:
            print(f"[WEB {self.call_id}] Agent: {full_response}")
            self.transcript.append({"role": "agent", "text": full_response})
            storage.append_transcript(self.call_id, "agent", full_response)
            self.messages.append({"role": "assistant", "content": full_response})
            await self._send_json({"type": "transcript", "role": "agent", "text": full_response})

    async def _speak(self, text: str, record_as: str = None):
        if not text.strip():
            return

        self.is_speaking = True
        # Don't mute STT — we need to hear backchannels and real interruptions
        # self.mute_stt = True
        self.chars_spoken += len(text)
        await self._send_json({"type": "speaking", "state": True})
        await self._send_json({"type": "cost_update", "chars": self.chars_spoken})
        voice_id = self.agent_config.get("voice_id", "PT4nqlKZfc06VW1BuClj")

        async def on_audio_chunk(chunk: bytes):
            if not self.is_speaking:
                raise asyncio.CancelledError()
            # Track chars played (rough: 4800 bytes ≈ 100ms ≈ ~15 chars of speech)
            self._chars_actually_played += max(1, len(chunk) // 320)
            if self.phone_fx:
                try:
                    chunk = phone_effect(chunk, sample_rate=24000, **self.phone_fx_settings)
                except Exception as e:
                    print(f"[PHONE_FX] Error: {e}", flush=True)
            b64 = base64.b64encode(chunk).decode("ascii")
            await self._send_json({"type": "audio_pcm", "data": b64})

        try:
            vs = self.agent_config.get("voice_settings", {})
            self.current_tts_task = asyncio.create_task(
                stream_tts(text, voice_id, on_audio_chunk,
                           output_format="pcm_24000", voice_settings=vs)
            )
            await self.current_tts_task
        except asyncio.CancelledError:
            pass
        finally:
            self.is_speaking = False
            # self.mute_stt = False
            await self._send_json({"type": "speaking", "state": False})

        if record_as:
            self.transcript.append({"role": record_as, "text": text})
            storage.append_transcript(self.call_id, record_as, text)
            self.messages.append({"role": "assistant", "content": text})
            await self._send_json({"type": "transcript", "role": record_as, "text": text})

    async def _stop_speaking(self):
        self.is_speaking = False
        if self.current_tts_task and not self.current_tts_task.done():
            self.current_tts_task.cancel()
        if self.current_llm_task and not self.current_llm_task.done():
            self.current_llm_task.cancel()
        # Truncate last assistant message to what was actually spoken
        # (user didn't hear the rest, so don't include it in context)
        if self._chars_actually_played > 0 and self.messages and self.messages[-1]["role"] == "assistant":
            full_text = self.messages[-1]["content"]
            # Estimate how much was played based on TTS chunks sent
            # Each chunk ≈ 100ms of audio, rough char estimate
            truncated = full_text[:self._chars_actually_played]
            if truncated and truncated != full_text:
                self.messages[-1]["content"] = truncated + "—"  # Mark as interrupted
                print(f"[WEB {self.call_id}] Truncated context: '{truncated[:50]}...'", flush=True)
        self._chars_actually_played = 0
        await self._send_json({"type": "clear_audio"})

    async def _send_json(self, data: dict):
        try:
            await self.ws.send_json(data)
        except Exception:
            pass

    async def stop(self):
        await self._stop_speaking()
        await self.stt.close()
        duration = 0
        if self.started_at:
            duration = (datetime.utcnow() - self.started_at).total_seconds()
        storage.update_call(self.call_id, status="completed",
                           duration_seconds=round(duration, 1),
                           transcript=self.transcript,
                           ended_at=datetime.utcnow().isoformat(),
                           cost_estimate_cents=round(self.chars_spoken * 0.03, 2))
        print(f"[WEB {self.call_id}] Ended. Duration: {duration:.0f}s")
