"""Audio format conversion utilities for Twilio <-> ElevenLabs pipeline."""
import base64
import struct

# μ-law encoding/decoding tables
MULAW_BIAS = 0x84
MULAW_CLIP = 32635
MULAW_TABLE = [
    0, 132, 396, 924, 1980, 4092, 8316, 16764
]

def pcm_to_mulaw(pcm_data: bytes) -> bytes:
    """Convert 16-bit PCM to μ-law (8-bit). Input: 16-bit signed LE PCM."""
    samples = struct.unpack(f"<{len(pcm_data)//2}h", pcm_data)
    mulaw_bytes = bytearray()
    for sample in samples:
        sign = 0
        if sample < 0:
            sign = 0x80
            sample = -sample
        if sample > MULAW_CLIP:
            sample = MULAW_CLIP
        sample += MULAW_BIAS
        
        exponent = 7
        for i in range(7, 0, -1):
            if sample >= MULAW_TABLE[i]:
                exponent = i
                break
        
        mantissa = (sample >> (exponent + 3)) & 0x0F
        mulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
        mulaw_bytes.append(mulaw_byte)
    
    return bytes(mulaw_bytes)


def mulaw_to_pcm(mulaw_data: bytes) -> bytes:
    """Convert μ-law (8-bit) to 16-bit PCM signed LE."""
    DECODE_TABLE = [
        -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
        -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
        -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
        -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
        -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
        -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
        -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
        -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
        -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
        -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
        -876, -844, -812, -780, -748, -716, -684, -652,
        -620, -588, -556, -524, -492, -460, -428, -396,
        -372, -356, -340, -324, -308, -292, -276, -260,
        -244, -228, -212, -196, -180, -164, -148, -132,
        -120, -112, -104, -96, -88, -80, -72, -64,
        -56, -48, -40, -32, -24, -16, -8, 0,
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
        15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
        11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
        7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
        5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
        3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
        2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
        1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
        1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
        876, 844, 812, 780, 748, 716, 684, 652,
        620, 588, 556, 524, 492, 460, 428, 396,
        372, 356, 340, 324, 308, 292, 276, 260,
        244, 228, 212, 196, 180, 164, 148, 132,
        120, 112, 104, 96, 88, 80, 72, 64,
        56, 48, 40, 32, 24, 16, 8, 0,
    ]
    pcm_bytes = bytearray()
    for b in mulaw_data:
        pcm_bytes += struct.pack("<h", DECODE_TABLE[b])
    return bytes(pcm_bytes)


def resample_8k_to_24k(pcm_8k: bytes) -> bytes:
    """Upsample 8kHz PCM to 24kHz (simple linear interpolation, 3x)."""
    samples = struct.unpack(f"<{len(pcm_8k)//2}h", pcm_8k)
    out = []
    for i in range(len(samples) - 1):
        s0, s1 = samples[i], samples[i + 1]
        out.append(s0)
        out.append(int(s0 + (s1 - s0) / 3))
        out.append(int(s0 + 2 * (s1 - s0) / 3))
    if samples:
        out.append(samples[-1])
        out.append(samples[-1])
        out.append(samples[-1])
    return struct.pack(f"<{len(out)}h", *out)


def resample_24k_to_8k(pcm_24k: bytes) -> bytes:
    """Downsample 24kHz PCM to 8kHz (take every 3rd sample)."""
    samples = struct.unpack(f"<{len(pcm_24k)//2}h", pcm_24k)
    out = [samples[i] for i in range(0, len(samples), 3)]
    return struct.pack(f"<{len(out)}h", *out)


def encode_twilio_audio(pcm_24k: bytes) -> str:
    """Convert 24kHz PCM to base64-encoded μ-law for Twilio."""
    pcm_8k = resample_24k_to_8k(pcm_24k)
    mulaw = pcm_to_mulaw(pcm_8k)
    return base64.b64encode(mulaw).decode("ascii")


def decode_twilio_audio(b64_mulaw: str) -> bytes:
    """Convert base64 μ-law from Twilio to 16-bit PCM 8kHz."""
    mulaw = base64.b64decode(b64_mulaw)
    return mulaw_to_pcm(mulaw)
