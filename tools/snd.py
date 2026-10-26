"""SND (Elecbyte sound container) writer/reader. Layout per Ikemen GO src/sound.go."""
import io
import struct
import wave

import numpy as np

SIG = b"ElecbyteSnd\x00"
RATE = 22050


def wav_bytes(samples, rate=RATE):
    """samples: float array in [-1,1] (mono)."""
    s = np.clip(np.asarray(samples, dtype=np.float64), -1, 1)
    pcm = (s * 32000).astype("<i2").tobytes()
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return b.getvalue()


def write_snd(path, sounds):
    """sounds: list of ((group, number), wav_bytes)."""
    hdr = bytearray(SIG)
    hdr += struct.pack("<HH", 0, 1)
    hdr += struct.pack("<II", len(sounds), 512)
    hdr += b"\x00" * (512 - len(hdr))
    out = bytearray(hdr)
    for i, ((g, n), data) in enumerate(sounds):
        start = len(out)
        nxt = start + 16 + len(data)
        if i == len(sounds) - 1:
            nxt = 0
        out += struct.pack("<IIii", nxt, len(data), g, n)
        out += data
    with open(path, "wb") as f:
        f.write(out)


def read_snd(path):
    d = open(path, "rb").read()
    assert d[:12] == SIG
    n, off = struct.unpack_from("<II", d, 16)
    res = {}
    for _ in range(n):
        nxt, ln, g, num = struct.unpack_from("<IIii", d, off)
        res[(g, num)] = d[off + 16: off + 16 + ln]
        off = nxt
    return res
