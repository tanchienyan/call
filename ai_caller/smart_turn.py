"""Smart Turn detection — ML-based end-of-turn prediction using Pipecat's v3.2 model."""
import numpy as np
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

_analyzer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = LocalSmartTurnAnalyzerV3()
        _analyzer.set_sample_rate(16000)
        print("[SMART_TURN] v3.2 model loaded", flush=True)
    return _analyzer


class TurnDetector:
    """Wraps Smart Turn for use in our pipeline.
    
    Usage:
        detector = TurnDetector()
        # Feed audio chunks as they come from the mic
        detector.feed_audio(pcm_bytes, is_speech=True)
        # When VAD detects silence, check if turn is actually complete
        is_done = await detector.is_turn_complete()
        # Reset for next turn
        detector.reset()
    """
    
    def __init__(self):
        self.analyzer = _get_analyzer()
        self.analyzer.clear()
    
    def feed_audio(self, pcm_16bit_bytes: bytes, is_speech: bool = True):
        """Feed raw 16-bit 16kHz PCM audio chunk."""
        self.analyzer.append_audio(pcm_16bit_bytes, is_speech)
    
    async def is_turn_complete(self) -> tuple[bool, float]:
        """Analyze if user has finished their turn.
        
        Returns: (is_complete, confidence)
        """
        try:
            state, metrics = await self.analyzer.analyze_end_of_turn()
            # EndOfTurnState: INCOMPLETE, COMPLETE, SILENCE_TIMEOUT
            is_complete = str(state) != "EndOfTurnState.INCOMPLETE"
            confidence = 0.0
            if metrics and hasattr(metrics, 'value'):
                confidence = metrics.value
            print(f"[SMART_TURN] state={state} conf={confidence:.2f}", flush=True)
            return is_complete, confidence
        except Exception as e:
            print(f"[SMART_TURN] Error: {e}", flush=True)
            return True, 0.5
    
    def reset(self):
        """Reset for next turn."""
        self.analyzer.clear()
