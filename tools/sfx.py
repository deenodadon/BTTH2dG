"""Synthesised sound effects and voice placeholders (numpy only).

Nothing here is sampled from the show: every sound is generated from noise and
oscillators.  Drop your own WAV clips into sounds/custom/<char>/<group>_<index>.wav
to replace any slot (see sounds/SLOTS.md, written by build.py)."""
import math

import numpy as np

RATE = 22050


def _t(dur):
    return np.arange(int(RATE * dur)) / RATE


def _rng(seed):
    return np.random.default_rng(seed)


def env(n, a=0.005, d=0.2, curve=4.0):
    t = np.arange(n) / RATE
    att = np.clip(t / max(a, 1e-4), 0, 1)
    dec = np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * (curve / 4))
    return att * dec


def lowpass(x, cutoff):
    """one-pole low-pass; cutoff may be an array (time-varying)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    a = 1 - np.exp(-2 * math.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def bandpass(x, f, q=2.0):
    """2-pole resonator (biquad bandpass), f may vary over time."""
    f = np.broadcast_to(np.asarray(f, dtype=np.float64), x.shape)
    y = np.zeros_like(x)
    y1 = y2 = x1 = x2 = 0.0
    for i in range(len(x)):
        w0 = 2 * math.pi * f[i] / RATE
        alpha = math.sin(w0) / (2 * q)
        b0, b2 = alpha, -alpha
        a0, a1, a2 = 1 + alpha, -2 * math.cos(w0), 1 - alpha
        yi = (b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, x[i]
        y2, y1 = y1, yi
        y[i] = yi
    return y


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def noise(dur, seed=0):
    return _rng(seed).uniform(-1, 1, int(RATE * dur))


# -- building blocks --------------------------------------------------------------


def whoosh(dur=0.22, f0=600, f1=2400, seed=1, peak=0.6):
    x = noise(dur, seed)
    n = len(x)
    f = np.linspace(f0, f1, n) * (1 + 0.5 * np.sin(np.linspace(0, math.pi, n)))
    y = bandpass(x, f, q=1.4)
    e = np.sin(np.linspace(0, math.pi, n)) ** 1.5
    return norm(y * e, peak)


def thump(dur=0.25, f0=120, f1=45, seed=2, crack=0.6, peak=0.9):
    t = _t(dur)
    n = len(t)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * math.pi * np.cumsum(f) / RATE
    body = np.sin(ph) * env(n, 0.002, dur * 0.35)
    cr = lowpass(noise(dur, seed), 3500) * env(n, 0.001, 0.03) * crack
    return norm(body + cr, peak)


def hit(level=1, seed=3):
    dur = [0.18, 0.26, 0.38][level]
    a = thump(dur, [160, 130, 110][level], [70, 50, 38][level], seed, crack=[0.8, 1.0, 1.2][level])
    sl = bandpass(noise(dur, seed + 9), 1800, q=0.8) * env(len(a), 0.001, 0.04) * 0.6
    return norm(a + sl, 0.95)


def block(seed=4):
    t = _t(0.16)
    n = len(t)
    tone = (np.sin(2 * math.pi * 1900 * t) + 0.5 * np.sin(2 * math.pi * 2870 * t)) * env(n, 0.001, 0.05)
    return norm(tone + bandpass(noise(0.16, seed), 3000, 1.0) * env(n, 0.001, 0.02), 0.7)


def fire(dur=0.7, seed=5, bright=1.0, peak=0.8):
    x = noise(dur, seed)
    n = len(x)
    roar = lowpass(x, 600 + 900 * bright) * 2.5
    hiss = bandpass(x, 2500 * bright, 0.7) * 0.5
    rng = _rng(seed + 1)
    crack = np.zeros(n)
    for _ in range(int(dur * 40)):
        i = rng.integers(0, n - 200)
        crack[i:i + 200] += rng.uniform(-1, 1, 200) * np.exp(-np.arange(200) / 30)
    e = np.minimum(np.linspace(0, 1, n) * 6, 1) * np.exp(-np.linspace(0, 3, n))
    return norm((roar + hiss + crack * 0.4) * e, peak)


def explosion(dur=1.6, seed=6, peak=0.95):
    x = noise(dur, seed)
    n = len(x)
    rum = lowpass(x, np.linspace(1800, 120, n)) * 3
    t = _t(dur)
    sub = np.sin(2 * math.pi * 48 * (1 - 0.4 * t / dur) * t) * np.exp(-t * 2.5)
    e = np.exp(-t * 2.2) * np.minimum(t / 0.01, 1)
    return norm(rum * e + sub * 0.8, peak)


def chime(freqs=(1760, 2637, 3520, 4699), dur=1.0, seed=7, peak=0.6):
    t = _t(dur)
    y = np.zeros_like(t)
    for i, f in enumerate(freqs):
        y += np.sin(2 * math.pi * f * t + i) * np.exp(-t * (3 + i)) / (1 + i * 0.5)
    shimmer = bandpass(noise(dur, seed), 6000, 2.0) * np.exp(-t * 5) * 0.4
    return norm(y + shimmer, peak)


def ice(seed=8):
    a = chime((2093, 3136, 4186, 5274), 0.9, seed)
    b = whoosh(0.5, 2000, 6000, seed + 1, 0.4)
    n = max(len(a), len(b))
    out = np.zeros(n)
    out[:len(a)] += a
    out[:len(b)] += b
    return norm(out, 0.75)


def eerie(dur=1.2, base=220, seed=9, peak=0.6):
    t = _t(dur)
    vib = 1 + 0.02 * np.sin(2 * math.pi * 5.5 * t)
    y = sum(np.sin(2 * math.pi * base * k * vib * t + k) / k for k in (1, 1.5, 2.01, 3.02))
    sw = np.minimum(t / (dur * 0.6), 1) * np.exp(-np.maximum(t - dur * 0.6, 0) * 6)
    return norm(y * sw + bandpass(noise(dur, seed), 900, 3.0) * sw * 0.6, peak)


def wind(dur=0.6, seed=10, peak=0.7):
    x = noise(dur, seed)
    n = len(x)
    f = 700 + 1800 * np.sin(np.linspace(0, math.pi, n)) ** 2
    y = bandpass(x, f, 3.0)
    return norm(y * np.sin(np.linspace(0, math.pi, n)), peak)


def slash(seed=11):
    a = whoosh(0.18, 1500, 5000, seed, 0.6)
    t = _t(0.35)
    ring = (np.sin(2 * math.pi * 3200 * t) + 0.6 * np.sin(2 * math.pi * 4700 * t)) * np.exp(-t * 14) * 0.5
    out = np.zeros(len(t))
    out[:len(a)] += a
    out += ring
    return norm(out, 0.8)


def hiss(dur=0.7, seed=12):
    x = noise(dur, seed)
    hp = x - lowpass(x, 3500)
    n = len(x)
    return norm(hp * np.minimum(np.linspace(0, 1, n) * 5, 1) * np.exp(-np.linspace(0, 2.5, n)), 0.6)


def bubbles(dur=0.9, seed=13):
    rng = _rng(seed)
    n = int(RATE * dur)
    y = np.zeros(n)
    for _ in range(int(dur * 22)):
        i = rng.integers(0, n - 2000)
        L = rng.integers(500, 1800)
        tt = np.arange(L) / RATE
        f = rng.uniform(300, 900) * (1 + 3 * tt / tt[-1])
        y[i:i + L] += np.sin(2 * math.pi * np.cumsum(f) / RATE) * np.exp(-tt * 30)
    return norm(y + lowpass(noise(dur, seed), 400) * 0.6, 0.6)


def gong(seed=14, dur=1.8, f=110):
    t = _t(dur)
    y = sum(np.sin(2 * math.pi * f * k * t) * np.exp(-t * (1.0 + k * 0.6)) / k for k in (1, 2.32, 3.9, 5.1, 6.7))
    att = lowpass(noise(dur, seed), 2000) * np.exp(-t * 30)
    return norm(y + att, 0.85)


def rise(dur=1.0, seed=15, f0=120, f1=900):
    t = _t(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * math.pi * np.cumsum(f) / RATE
    y = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sign(np.sin(ph * 0.5))) * np.minimum(t / dur * 1.3, 1)
    r = fire(dur, seed, 1.0, 0.6)
    return norm(y * 0.4 + r[:len(y)], 0.85)


def arpeggio(notes=(523, 659, 784, 1047, 1319), step=0.07, seed=16):
    out = np.zeros(int(RATE * (step * len(notes) + 0.6)))
    for i, f in enumerate(notes):
        t = _t(0.6)
        s = (np.sin(2 * math.pi * f * t) + 0.3 * np.sin(4 * math.pi * f * t)) * np.exp(-t * 6)
        j = int(i * step * RATE)
        out[j:j + len(s)] += s
    return norm(out, 0.6)


def step(seed=17):
    return norm(lowpass(noise(0.08, seed), 500) * env(int(RATE * 0.08), 0.002, 0.02), 0.4)


def land(seed=18):
    return thump(0.16, 90, 40, seed, crack=0.3, peak=0.55)


# -- voice placeholders ---------------------------------------------------------------

VOWELS = {"a": (800, 1200, 2500), "e": (500, 1900, 2600), "i": (320, 2300, 3000),
          "o": (500, 900, 2400), "u": (350, 800, 2300), "h": (700, 1300, 2500)}


def voice(syll="ha", pitch=130, dur=0.3, seed=20, shape="shout", female=False, breathy=0.15):
    """Formant-synth 'kiai': syllable is 'h'/consonant + vowel."""
    t = _t(dur)
    n = len(t)
    if shape == "shout":
        p = pitch * (1.15 - 0.3 * t / dur)
    elif shape == "rise":
        p = pitch * (0.9 + 0.5 * t / dur)
    elif shape == "pain":
        p = pitch * (1.4 - 0.7 * (t / dur) ** 0.7)
    else:
        p = pitch * np.ones(n)
    p = p * (1 + 0.012 * np.sin(2 * math.pi * 6 * t))
    ph = np.cumsum(p) / RATE
    src = 2 * (ph % 1.0) - 1  # saw (glottal-ish)
    src = lowpass(src, 3000)
    src += noise(dur, seed) * breathy
    v = syll[-1]
    f1, f2, f3 = VOWELS.get(v, VOWELS["a"])
    if female:
        f1, f2, f3 = f1 * 1.15, f2 * 1.18, f3 * 1.1
    y = bandpass(src, f1, 6) * 1.0 + bandpass(src, f2, 8) * 0.6 + bandpass(src, f3, 10) * 0.3
    if syll[0] in "hs":
        asp = bandpass(noise(dur, seed + 3), f2 if syll[0] == "h" else 5000, 1.5)
        k = np.clip(1 - t / 0.06, 0, 1)
        y = y * np.clip(t / 0.05, 0, 1) + asp * k * 0.6
    e = np.minimum(t / 0.02, 1) * np.clip((dur - t) / (dur * 0.35), 0, 1)
    return norm(y * e, 0.8)


def mix(*parts, gap=0.0):
    out = np.zeros(sum(len(p) for p in parts) + int(gap * RATE * len(parts)))
    i = 0
    for p in parts:
        out[i:i + len(p)] += p
        i += len(p) + int(gap * RATE)
    return out[:i]


def layer(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return norm(out, 0.9)


VOICES = {
    "xiaoyan": dict(pitch=135, female=False),
    "yaolao": dict(pitch=98, female=False, breathy=0.3),
    "xuner": dict(pitch=255, female=True),
    "medusa": dict(pitch=215, female=True),
    "yunyun": dict(pitch=240, female=True),
    "fairydoctor": dict(pitch=265, female=True, breathy=0.25),
}


def char_sounds(key):
    """Return {(group, index): (samples, description)} for one fighter."""
    v = VOICES[key]
    vo = lambda s, sh="shout", d=0.28, sd=0, pm=1.0: voice(s, v["pitch"] * pm, d, 30 + sd, sh, v["female"],
                                                           v.get("breathy", 0.15))
    S = {}
    # 0: voices
    S[(0, 0)] = (vo("ha", d=0.18), "voice: light attack grunt")
    S[(0, 1)] = (vo("hya", d=0.3, sd=1), "voice: heavy attack shout")
    S[(0, 2)] = (vo("ho", d=0.35, sd=2, pm=0.95), "voice: special move shout")
    S[(0, 3)] = (mix(vo("ha", d=0.2, sd=3), vo("a", "rise", 0.5, 4)), "voice: super move cry")
    S[(0, 4)] = (vo("u", "pain", 0.25, 5, 1.1), "voice: hurt (light)")
    S[(0, 5)] = (vo("a", "pain", 0.45, 6, 1.15), "voice: hurt (heavy)")
    S[(0, 6)] = (vo("a", "pain", 1.0, 7, 1.2), "voice: KO scream")
    S[(0, 7)] = (mix(vo("hm", "flat", 0.25, 8), vo("ha", "shout", 0.3, 9)), "voice: win / taunt")
    S[(0, 8)] = (vo("he", "rise", 0.3, 10), "voice: intro")
    S[(0, 9)] = (vo("hu", "shout", 0.22, 11), "voice: throw")
    # 1: swings & movement
    S[(1, 0)] = (whoosh(0.16, 900, 2600, 40), "swing light")
    S[(1, 1)] = (whoosh(0.28, 400, 1600, 41, 0.75), "swing heavy")
    S[(1, 2)] = (step(42), "footstep")
    S[(1, 3)] = (land(43), "landing")
    S[(1, 4)] = (whoosh(0.35, 300, 1200, 44, 0.5), "dash / jump")
    # 2: impacts
    S[(2, 0)] = (hit(0, 50), "hit light")
    S[(2, 1)] = (hit(1, 51), "hit medium")
    S[(2, 2)] = (hit(2, 52), "hit heavy")
    S[(2, 3)] = (block(53), "block")
    S[(2, 4)] = (thump(0.5, 80, 30, 54, crack=1.4), "body slam / fall")
    # 3: character specific
    if key == "xiaoyan":
        S[(3, 0)] = (layer(fire(0.5, 60), thump(0.3, 140, 50, 61)), "Octane Blast detonation")
        S[(3, 1)] = (layer(fire(1.0, 62, 0.8), thump(0.6, 90, 35, 63, 1.5)), "Flame Splitting Tsunami")
        S[(3, 2)] = (fire(0.6, 64, 1.2), "rising flame")
        S[(3, 3)] = (rise(1.4, 65), "Skyfire Three Mysterious Change power-up")
        S[(3, 4)] = (layer(eerie(1.6, 330, 66, 0.5), fire(1.6, 67, 1.3, 0.5)), "Lotus forming")
        S[(3, 5)] = (explosion(2.4, 68), "Buddha's Angry Lotus explosion")
    elif key == "yaolao":
        S[(3, 0)] = (layer(ice(70), fire(0.6, 71, 1.6, 0.5)), "Bone Chilling Flame")
        S[(3, 1)] = (eerie(0.9, 180, 72), "Soul Shock")
        S[(3, 2)] = (arpeggio(seed=73), "Alchemy pill / heal")
        S[(3, 3)] = (layer(wind(0.5, 74), chime((1300, 1950), 0.5, 75, 0.3)), "Spirit drift teleport")
        S[(3, 4)] = (layer(ice(76), fire(2.0, 77, 1.6, 0.6)), "Bone Chilling Flame torrent")
        S[(3, 5)] = (layer(eerie(1.8, 110, 78), explosion(1.8, 79, 0.7)), "Soul Realm palm")
    elif key == "xuner":
        S[(3, 0)] = (layer(gong(80, 1.0, 220), whoosh(0.3, 800, 3000, 81, 0.4)), "Emperor Seal")
        S[(3, 1)] = (fire(0.8, 82, 1.1), "Golden flame rise")
        S[(3, 2)] = (whoosh(0.4, 600, 2600, 83), "Ocean Reversal flip")
        S[(3, 3)] = (gong(84, 1.6, 150), "Seal impact")
        S[(3, 4)] = (layer(fire(2.4, 85, 1.0), gong(86, 2.4, 90)), "Golden Emperor Burning Heaven Flame")
    elif key == "medusa":
        S[(3, 0)] = (layer(fire(0.7, 90, 0.9), hiss(0.5, 91)), "Venomous Flame")
        S[(3, 1)] = (layer(hiss(0.4, 92), whoosh(0.3, 500, 2500, 93)), "Serpent lunge")
        S[(3, 2)] = (eerie(1.0, 140, 94), "Spatial seal")
        S[(3, 3)] = (layer(hiss(1.2, 95), thump(1.0, 70, 30, 96, 1.2), wind(1.2, 97)), "Seven-Coloured Python")
        S[(3, 4)] = (layer(eerie(1.4, 90, 98), explosion(1.4, 99, 0.7)), "Spatial collapse")
    elif key == "yunyun":
        S[(3, 0)] = (layer(slash(100), wind(0.5, 101)), "Wind blade")
        S[(3, 1)] = (wind(0.8, 102), "Rising gale")
        S[(3, 2)] = (layer(whoosh(0.3, 2000, 6000, 103, 0.5), chime((1500, 2250), 0.4, 104, 0.3)), "Wind step")
        S[(3, 3)] = (wind(2.0, 105), "Sword storm tornado")
        S[(3, 4)] = (layer(slash(106), chime((2600, 3900), 0.6, 107, 0.4)), "Falling wind sword")
    elif key == "fairydoctor":
        S[(3, 0)] = (layer(bubbles(0.9, 110), hiss(0.6, 111)), "Poison mist")
        S[(3, 1)] = (layer(thump(0.3, 130, 50, 112), bubbles(0.5, 113)), "Toxic palm")
        S[(3, 2)] = (bubbles(1.2, 114), "Poison field")
        S[(3, 3)] = (layer(eerie(1.6, 160, 115), bubbles(1.6, 116)), "Woeful Poison Body unleashed")
        S[(3, 4)] = (layer(hiss(2.0, 117), bubbles(2.0, 118)), "Poison calamity rain")
    # 4: super flash
    S[(4, 0)] = (layer(chime((880, 1320, 1760), 0.8, 120, 0.5), whoosh(0.5, 300, 3000, 121, 0.5)), "super flash")
    return S
