"""Phone line audio effects — make TTS sound like it's coming through a real phone."""
import numpy as np
from scipy.signal import butter, lfilter


def _bandpass(data: np.ndarray, sr: int, low=300, high=3400, order=4):
    """Telephone bandpass filter (ITU G.712: 300-3400 Hz)."""
    nyq = sr / 2
    b, a = butter(order, [low / nyq, high / nyq], btype='band')
    return lfilter(b, a, data)


def _add_noise(data: np.ndarray, level=0.002):
    """Subtle line noise."""
    noise = np.random.normal(0, level, len(data))
    return data + noise


def _soft_clip(data: np.ndarray, threshold=0.85):
    """Gentle analog-style saturation."""
    return np.tanh(data / threshold) * threshold


def phone_effect(pcm_bytes: bytes, sample_rate: int = 24000,
                 bandpass=True, noise_level=0.006,
                 clip=True, gain_db=-3.0,
                 bandpass_low=300, bandpass_high=3400,
                 clip_threshold=0.70, **kwargs) -> bytes:
    """Apply phone-line effects to 16-bit PCM audio.
    
    Args:
        pcm_bytes: Raw 16-bit signed LE PCM
        sample_rate: Sample rate (default 24000)
        bandpass: Apply telephone bandpass filter (300-3400 Hz)
        noise_level: Background noise amplitude (0 = off, 0.002 = subtle)
        clip: Apply soft clipping / saturation
        gain_db: Overall gain adjustment in dB
    
    Returns:
        Processed 16-bit PCM bytes, same length
    """
    if len(pcm_bytes) < 4:
        return pcm_bytes
    
    # Decode to float
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float64) / 32768.0
    
    # Bandpass: telephone frequency range
    if bandpass and len(samples) > 50:
        samples = _bandpass(samples, sample_rate, low=bandpass_low, high=bandpass_high)
    
    # Subtle line noise
    if noise_level > 0:
        samples = _add_noise(samples, noise_level)
    
    # Soft saturation (like phone codec compression)
    if clip:
        samples = _soft_clip(samples, threshold=clip_threshold)
    
    # Gain adjustment
    if gain_db != 0:
        samples *= 10 ** (gain_db / 20)
    
    # Back to int16
    samples = np.clip(samples * 32768, -32768, 32767).astype(np.int16)
    return samples.tobytes()
