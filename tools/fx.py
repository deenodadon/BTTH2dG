"""Procedural effect sprites: Heavenly Flames, seals, wind, poison mist, the seven-coloured python...

Every effect returns dict(frames=[(rgba uint8 HxWx4, (axis_x, axis_y))], t=ticks, loop=idx|None,
trans="add"|None, clsn1=(x0,y0,x1,y1) in AIR coords or None)."""
import math

import numpy as np

from render3d import Canvas, Mat

RNG = np.random.default_rng(7)


# ---------------------------------------------------------------------------
# noise helpers


def _smooth(t):
    return t * t * (3 - 2 * t)


def value_noise(h, w, cell, seed):
    rng = np.random.default_rng(seed)
    gh, gw = h // cell + 3, w // cell + 3
    g = rng.random((gh, gw)).astype(np.float32)
    ys = np.arange(h, dtype=np.float32) / cell
    xs = np.arange(w, dtype=np.float32) / cell
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    fy = _smooth(ys - y0)[:, None]
    fx = _smooth(xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(h, w, cell, seed, oct=4):
    tot = np.zeros((h, w), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(oct):
        c = max(2, cell // (2 ** o))
        tot += amp * value_noise(h, w, c, seed + o * 101)
        norm += amp
        amp *= 0.5
    return tot / norm


def grid(w, h, cx, cy):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs - cx, ys - cy


def ramp(stops, v):
    """stops: [(pos, (r,g,b))] ascending.  v: array 0..1 -> rgb float."""
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,), np.float32)
    pos = [s[0] for s in stops]
    cols = [np.array(s[1], np.float32) for s in stops]
    for i in range(len(stops) - 1):
        p0, p1 = pos[i], pos[i + 1]
        m = (v >= p0) & (v <= p1)
        k = ((v - p0) / max(p1 - p0, 1e-6))[m][:, None]
        out[m] = cols[i] * (1 - k) + cols[i + 1] * k
    out[v > pos[-1]] = cols[-1]
    return out


def to_rgba(rgb, alpha_mask):
    img = np.zeros(rgb.shape[:2] + (4,), np.uint8)
    img[..., :3] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    img[..., 3] = np.where(alpha_mask, 255, 0).astype(np.uint8)
    return img


# colour sets ----------------------------------------------------------------
FIRE_GREEN = [(0.0, (0.0, 0.05, 0.04)), (0.25, (0.02, 0.35, 0.22)), (0.5, (0.1, 0.8, 0.55)),
              (0.75, (0.6, 1.0, 0.8)), (1.0, (1.0, 1.0, 0.95))]
FIRE_ORANGE = [(0.0, (0.06, 0.0, 0.0)), (0.3, (0.55, 0.08, 0.02)), (0.55, (1.0, 0.45, 0.08)),
               (0.8, (1.0, 0.85, 0.4)), (1.0, (1.0, 1.0, 0.9))]
FIRE_WHITE = [(0.0, (0.0, 0.02, 0.06)), (0.3, (0.12, 0.3, 0.55)), (0.6, (0.55, 0.8, 1.0)),
              (0.85, (0.9, 0.97, 1.0)), (1.0, (1.0, 1.0, 1.0))]
FIRE_GOLD = [(0.0, (0.05, 0.02, 0.0)), (0.3, (0.55, 0.3, 0.02)), (0.6, (1.0, 0.75, 0.15)),
             (0.85, (1.0, 0.95, 0.6)), (1.0, (1.0, 1.0, 0.95))]
FIRE_VENOM = [(0.0, (0.04, 0.0, 0.06)), (0.3, (0.35, 0.05, 0.5)), (0.6, (0.6, 0.2, 0.85)),
              (0.8, (0.55, 0.95, 0.45)), (1.0, (0.95, 1.0, 0.85))]
WIND = [(0.0, (0.0, 0.04, 0.03)), (0.35, (0.15, 0.4, 0.35)), (0.7, (0.55, 0.95, 0.8)),
        (1.0, (0.95, 1.0, 1.0))]
SOUL = [(0.0, (0.0, 0.02, 0.05)), (0.4, (0.1, 0.35, 0.5)), (0.75, (0.45, 0.85, 0.95)),
        (1.0, (0.95, 1.0, 1.0))]
POISON = [(0.0, (0.16, 0.13, 0.2)), (0.4, (0.32, 0.25, 0.4)), (0.7, (0.5, 0.42, 0.6)),
          (1.0, (0.72, 0.66, 0.8))]
DUST = [(0.0, (0.35, 0.32, 0.28)), (1.0, (0.85, 0.8, 0.72))]


def flame_field(w, h, cx, cy, shape_fn, t, seed, cell=18, rise=(0.0, 1.0), speed=7.0):
    """Generic animated flame: intensity = shape * turbulence (scrolling)."""
    big = fbm(h + 200, w + 200, cell, seed)
    X, Y = grid(w, h, cx, cy)
    oy = int(100 + rise[1] * speed * t) % 100
    ox = int(100 - rise[0] * speed * t) % 100
    n = big[oy:oy + h, ox:ox + w]
    s = shape_fn(X, Y)
    return np.clip(s * (0.55 + 0.9 * n) - 0.25 * (1 - n), 0, 1.4)


def fireball(stops, rx=34, ry=26, tail=70, n=6, seed=1, wobble=1.0):
    w, h = int(rx * 2 + tail + 30), int(ry * 2 + 40)
    cx, cy = w - rx - 14, h / 2
    frames = []
    for t in range(n):
        def shape(X, Y):
            xx = np.where(X < 0, X / (rx + tail), X / rx)
            d = np.sqrt(xx ** 2 + (Y / (ry * (1 + 0.25 * np.clip(-X / (rx + tail), 0, 1)))) ** 2)
            return np.clip(1.15 - d, 0, 1) * 1.7
        v = flame_field(w, h, cx, cy, shape, t * wobble, seed, cell=16, rise=(1.0, 0.25), speed=9)
        frames.append((to_rgba(ramp(stops, v), v > 0.16), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add",
                clsn1=(-rx, -ry, rx, ry))


def burst(stops, r=60, n=9, seed=3, ring=True):
    w = h = int(r * 2.6)
    cx = cy = w / 2
    frames = []
    for t in range(n):
        k = (t + 1) / n
        rad = r * (0.35 + 0.75 * k)

        def shape(X, Y):
            d = np.sqrt(X * X + Y * Y) / rad
            core = np.clip(1.1 - d, 0, 1) * (1.6 - 1.3 * k)
            if ring:
                core = np.maximum(core, np.clip(1 - abs(d - 1) * 5, 0, 1) * (1.2 - k))
            return core
        v = flame_field(w, h, cx, cy, shape, t, seed, cell=14, rise=(0, 1), speed=5)
        frames.append((to_rgba(ramp(stops, v), v > 0.18), (int(cx), int(cy))))
    return dict(frames=frames, t=2, loop=None, trans="add", clsn1=None)


def column(stops, w=110, h=300, n=8, seed=5, base_w=None):
    W, H = w + 60, h + 40
    cx, cy = W / 2, H - 10
    frames = []
    for t in range(n):
        def shape(X, Y):
            yy = -Y / h
            half = (w / 2) * (0.55 + 0.45 * np.sqrt(np.clip(yy, 0, 1)))
            s = np.clip(1 - np.abs(X) / half, 0, 1) * np.clip(1.05 - yy, 0, 1) * 1.8
            return s * (Y < 4)
        v = flame_field(W, H, cx, cy, shape, t, seed, cell=20, rise=(0, 1.0), speed=14)
        frames.append((to_rgba(ramp(stops, v), v > 0.16), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-w // 2, -h, w // 2, 0))


def aura(stops, w=150, h=230, n=6, seed=9):
    W, H = w + 60, h + 70
    cx, cy = W / 2, H - 20
    frames = []
    for t in range(n):
        def shape(X, Y):
            yy = -Y / h
            ex = X / (w / 2 * (0.8 + 0.3 * np.sin(np.clip(yy, 0, 1) * math.pi)))
            ey = (yy - 0.45) / 0.62
            d = np.sqrt(ex ** 2 + ey ** 2)
            return np.clip(1 - np.abs(d - 0.92) * 3.2, 0, 1) * 1.4 + np.clip(0.8 - d, 0, 1) * 0.2
        v = flame_field(W, H, cx, cy, shape, t, seed, cell=14, rise=(0, 1.0), speed=12)
        frames.append((to_rgba(ramp(stops, v), v > 0.2), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=None)


def wave(stops, w=150, h=170, n=6, seed=11):
    """Ground-travelling crescent of fire (Flame Splitting Tsunami)."""
    W, H = w + 40, h + 30
    cx, cy = W / 2 + 20, H - 8
    frames = []
    for t in range(n):
        def shape(X, Y):
            yy = -Y / h
            front = 30 * np.sin(np.clip(yy, 0, 1) * math.pi * 0.9)
            d = (X - front) / (w * 0.32)
            s = np.clip(1 - np.abs(d + 0.3) * 1.4, 0, 1) * np.clip(1.05 - yy, 0, 1) * (Y < 3) * 1.9
            return s
        v = flame_field(W, H, cx, cy, shape, t, seed, cell=16, rise=(1.0, 1.0), speed=12)
        frames.append((to_rgba(ramp(stops, v), v > 0.17), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-w // 2, -h + 20, w // 2, 0))


def crescent(stops, r=55, n=4, seed=13):
    w, h = int(r * 2.2), int(r * 2.6)
    cx, cy = w / 2 - 10, h / 2
    frames = []
    for t in range(n):
        X, Y = grid(w, h, cx, cy)
        d1 = np.sqrt(X * X + (Y * 0.85) ** 2) / r
        d2 = np.sqrt((X + r * 0.45) ** 2 + (Y * 0.85) ** 2) / r
        s = np.clip((1 - d1) * 6, 0, 1) * np.clip((d2 - 0.85) * 4, 0, 1)
        n_ = fbm(h, w, 8, seed + t)
        streak = 0.75 + 0.5 * np.sin(Y * 0.5 + t * 2.0 + n_ * 4)
        v = s * streak * (0.7 + 0.5 * n_) * 1.3
        frames.append((to_rgba(ramp(stops, v), v > 0.15), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-r // 3, -r, r, r))


def ring(stops, r=90, n=10, thick=0.12, seed=17):
    w = h = int(r * 2.4)
    cx = cy = w / 2
    frames = []
    for t in range(n):
        k = (t + 1) / n
        X, Y = grid(w, h, cx, cy)
        d = np.sqrt(X * X + (Y * 1.25) ** 2) / (r * (0.3 + 0.7 * k))
        nz = fbm(h, w, 10, seed + t)
        v = np.clip(1 - np.abs(d - 1) / thick, 0, 1) * (1.3 - 0.7 * k) * (0.6 + 0.6 * nz)
        v = np.maximum(v, np.clip(0.8 - d, 0, 1) * 0.35 * (1 - k) * nz)
        frames.append((to_rgba(ramp(stops, v), v > 0.15), (int(cx), int(cy))))
    return dict(frames=frames, t=2, loop=None, trans="add", clsn1=None)


def seal(stops, r=60, n=6, seed=19):
    """Rotating golden emperor seal: concentric rings, spokes and runic strokes."""
    w = h = int(r * 2.3)
    cx = cy = w / 2
    rng = np.random.default_rng(seed)
    strokes = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.35, 0.62), rng.uniform(0.15, 0.5)) for _ in range(14)]
    frames = []
    for t in range(n):
        X, Y = grid(w, h, cx, cy)
        Y2 = Y * 1.0
        d = np.sqrt(X * X + Y2 * Y2) / r
        th = np.arctan2(Y2, X) + t * (2 * math.pi / n / 6)
        v = np.clip(1 - np.abs(d - 0.95) * 30, 0, 1) + np.clip(1 - np.abs(d - 0.8) * 40, 0, 1) * 0.9
        v += np.clip(1 - np.abs(d - 0.3) * 30, 0, 1) * 0.9
        sp = (np.abs(((th * 8 / math.pi) % 2) - 1) < 0.08) & (d > 0.8) & (d < 0.95)
        v = np.maximum(v, sp * 1.0)
        for a0, rr, ln in strokes:
            # small arc strokes inside ring (glyphs)
            da = np.abs(((th - a0 + math.pi) % (2 * math.pi)) - math.pi)
            v = np.maximum(v, ((np.abs(d - rr) < 0.025) & (da < ln)) * 0.95)
            v = np.maximum(v, ((np.abs(da - ln) < 0.03) & (np.abs(d - rr - 0.08) < 0.08)) * 0.95)
        glow = np.clip(1 - d, 0, 1) * 0.35
        v = np.maximum(v, glow) * (d < 1.05)
        frames.append((to_rgba(ramp(stops, v), v > 0.12), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-int(r * 0.8), -int(r * 0.8), int(r * 0.8), int(r * 0.8)))


def lotus(scale=1.0, n=8, seed=23):
    """Buddha's Angry Lotus: petals of different Heavenly Flames."""
    R = int(70 * scale)
    w = h = int(R * 2.6)
    cx, cy = w / 2, h / 2
    petal_cols = [FIRE_GREEN, FIRE_WHITE, FIRE_GOLD, FIRE_VENOM, FIRE_ORANGE]
    frames = []
    for t in range(n):
        X, Y = grid(w, h, cx, cy)
        th = np.arctan2(Y, X)
        d = np.sqrt(X * X + Y * Y) / R
        nz = fbm(h, w, 10, seed + t)
        best = np.zeros((h, w), np.float32)
        rgb = np.zeros((h, w, 3), np.float32)
        for layer, (count, rr, off) in enumerate(((8, 1.0, 0.0), (8, 0.75, math.pi / 8), (5, 0.45, 0.3))):
            for i in range(count):
                a = off + i * 2 * math.pi / count + t * 0.08 * (1 if layer % 2 == 0 else -1)
                # petal = ellipse along direction a
                ux = X * math.cos(a) + Y * math.sin(a)
                uy = -X * math.sin(a) + Y * math.cos(a)
                pv = np.clip(1 - np.sqrt(((ux / R - rr * 0.55) / (rr * 0.5)) ** 2 + (uy / R / (rr * 0.2)) ** 2), 0, 1)
                pv = pv * (0.7 + 0.6 * nz) * 1.6
                cs = petal_cols[(i + layer) % len(petal_cols)]
                m = pv > best
                rgb[m] = ramp(cs, pv)[m]
                best = np.maximum(best, pv)
        core = np.clip(1 - d / 0.25, 0, 1) * 1.5
        m = core > best
        rgb[m] = ramp(FIRE_WHITE, core)[m]
        best = np.maximum(best, core)
        frames.append((to_rgba(rgb, best > 0.12), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-int(R * 0.8), -int(R * 0.8), int(R * 0.8), int(R * 0.8)))


def big_explosion(n=16, R=230, seed=29):
    """Lotus detonation: multi-coloured blast that fills the screen."""
    w = h = int(R * 2.3)
    cx, cy = w / 2, h / 2 + 20
    frames = []
    for t in range(n):
        k = (t + 1) / n
        X, Y = grid(w, h, cx, cy)
        d = np.sqrt(X * X + (Y * 1.15) ** 2) / (R * (0.25 + 0.8 * k ** 0.6))
        nz = fbm(h, w, 26, seed + t * 3)
        v = np.clip(1.15 - d, 0, 1) * (1.7 - 1.2 * k) * (0.5 + 0.8 * nz)
        th = np.arctan2(Y, X)
        wa = ((np.sin(th * 3 + t * 0.5 + nz * 4) + 1) / 2)[..., None]
        wb = ((np.sin(th * 2 - t * 0.4 + 2 + nz * 3) + 1) / 2)[..., None]
        rgbA = ramp(FIRE_GREEN, v)
        rgbB = ramp(FIRE_GOLD, v)
        rgbC = ramp(FIRE_VENOM, v)
        mix = (rgbA * wa + rgbB * (1 - wa)) * wb + rgbC * (1 - wb)
        white = np.clip(v - 0.9, 0, 1)[..., None] * 2
        rgb = np.clip(mix + white, 0, 1)
        frames.append((to_rgba(rgb, v > 0.14), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=None, trans="add",
                clsn1=(-int(R * 0.9), -int(R * 0.9), int(R * 0.9), int(R * 0.9)))


def cloud(stops, w=150, h=110, n=8, seed=31, puffy=1.0):
    W, H = w + 30, h + 30
    cx, cy = W / 2, H / 2
    frames = []
    for t in range(n):
        X, Y = grid(W, H, cx, cy)
        d = np.sqrt((X / (w / 2)) ** 2 + (Y / (h / 2)) ** 2)
        nz = fbm(H + 60, W + 60, 22, seed)[(t * 4) % 60:(t * 4) % 60 + H, (t * 3) % 60:(t * 3) % 60 + W]
        v = (1.05 - d) * 1.2 + (nz - 0.5) * 1.1 * puffy
        shade = np.clip(0.4 + (nz - 0.5) * 1.2 - Y / h * 0.4, 0, 1)
        frames.append((to_rgba(ramp(stops, shade), v > 0.2), (int(cx), int(cy))))
    return dict(frames=frames, t=5, loop=0, trans=None,
                clsn1=(-int(w * 0.42), -int(h * 0.42), int(w * 0.42), int(h * 0.42)))


def sphere_vortex(stops, r=80, n=10, seed=37, implode=False):
    w = h = int(r * 2.5)
    cx = cy = w / 2
    frames = []
    for t in range(n):
        k = (t + 1) / n
        X, Y = grid(w, h, cx, cy)
        rad = r * ((1.1 - 0.9 * k) if implode else (0.4 + 0.6 * k))
        d = np.sqrt(X * X + Y * Y) / rad
        th = np.arctan2(Y, X)
        swirl = np.sin(th * 5 + d * 9 - t * 1.3) * 0.5 + 0.5
        v = np.clip(1 - np.abs(d - 0.85) * 4, 0, 1) * 1.2 + np.clip(0.9 - d, 0, 1) * swirl * 0.9
        frames.append((to_rgba(ramp(stops, v), v > 0.15), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=None, trans="add", clsn1=(-int(r * 0.7), -int(r * 0.7), int(r * 0.7), int(r * 0.7)))


def beam(stops, length=420, wid=70, n=4, seed=41):
    W, H = length + 40, wid + 50
    cx, cy = 10, H / 2
    frames = []
    for t in range(n):
        def shape(X, Y):
            prof = np.clip(1 - np.abs(Y) / (wid / 2 * (0.75 + 0.25 * np.clip(X / 60, 0, 1))), 0, 1)
            endfade = np.clip((length - X) / 40, 0, 1) * np.clip((X + 10) / 20, 0, 1)
            return prof * endfade * 1.6
        v = flame_field(W, H, cx, cy, shape, t, seed, cell=14, rise=(-1.0, 0.2), speed=18)
        frames.append((to_rgba(ramp(stops, v), v > 0.16), (int(cx), int(cy))))
    return dict(frames=frames, t=2, loop=0, trans="add", clsn1=(0, -wid // 2 + 6, length - 20, wid // 2 - 6))


def tornado(stops, w=140, h=280, n=6, seed=43):
    W, H = w + 60, h + 30
    cx, cy = W / 2, H - 6
    frames = []
    for t in range(n):
        X, Y = grid(W, H, cx, cy)
        yy = np.clip(-Y / h, 0, 1)
        half = w / 2 * (0.25 + 0.75 * yy)
        sway = 10 * np.sin(yy * 6 + t)
        u = (X - sway) / half
        bands = np.sin(yy * 40 - u * 3 + t * 1.6) * 0.5 + 0.5
        v = np.clip(1 - np.abs(u), 0, 1) ** 0.5 * (0.45 + 0.75 * bands) * (Y < 2) * np.clip(1.05 - yy, 0, 1) * 1.4
        frames.append((to_rgba(ramp(stops, v), v > 0.18), (int(cx), int(cy))))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=(-w // 2, -h, w // 2, 0))


def python_serpent(n=6, length=520, seed=47):
    """Seven-Coloured Sky Swallowing Python rushing forward (axis at the head)."""
    W, H = length + 120, 230
    hx, hy = W - 70, H / 2
    rainbow = [(1.0, 0.2, 0.2), (1.0, 0.55, 0.1), (1.0, 0.9, 0.2), (0.2, 0.9, 0.3), (0.2, 0.7, 1.0),
               (0.35, 0.3, 1.0), (0.75, 0.3, 0.95)]
    frames = []
    for t in range(n):
        cv = Canvas(xmin=-W + 70, xmax=70, ymin=-H / 2, ymax=H / 2)
        segs = 26
        pts = []
        for i in range(segs + 1):
            u = i / segs
            x = -u * length
            y = 34 * math.sin(u * 7 - t * (2 * math.pi / n)) * (0.3 + u)
            pts.append((x, y))
        for i in range(segs):
            u = i / segs
            col = rainbow[int(u * 7) % 7]
            m = Mat(col, spec=0.4, outline=0.35, rim=0.3)
            r0 = 34 * (1 - u * 0.75) + 4
            r1 = 34 * (1 - (i + 1) / segs * 0.75) + 4
            cv.capsule((pts[i][0], pts[i][1], 0), (pts[i + 1][0], pts[i + 1][1], 0), r0, r1, m)
        head = Mat((0.95, 0.3, 0.35), spec=0.5, outline=0.35)
        cv.ellipsoid((22, pts[0][1] + 4, 4), 48, 30, 30, 0, head)
        cv.ellipsoid((40, pts[0][1] - 10, 10), 34, 14, 22, -10, Mat((0.9, 0.85, 0.4), outline=0.4))
        cv.ellipsoid((34, pts[0][1] + 16, 30), 7, 5, 4, 0, Mat((1.0, 0.95, 0.2), spec=0.6, outline=0.6))
        for j in range(3):
            cv.capsule((10 - j * 12, pts[0][1] + 26, 6), (-10 - j * 14, pts[0][1] + 40 + j * 4, 2), 5, 1.5,
                       Mat(rainbow[j * 2], outline=0.4))
        img, origin = cv.shade()
        frames.append((img, (int(origin[0] + 0), int(origin[1]))))
    return dict(frames=frames, t=3, loop=0, trans=None, clsn1=(-length + 60, -60, 90, 60))


def spectral_hand(n=10):
    """Giant soul palm descending (Yao Lao's Soul Realm Domination)."""
    frames = []
    m = Mat((0.55, 0.9, 1.0), spec=0.3, outline=0.6, rim=0.5)
    for t in range(n):
        k = t / (n - 1)
        cv = Canvas(xmin=-170, xmax=170, ymin=-20, ymax=420)
        y0 = 360 - 330 * min(1.0, k * 1.4)
        cv.ellipsoid((0, y0 + 60, 0), 70, 85, 30, 0, m)
        for j, dx in enumerate((-48, -18, 14, 44)):
            ln = 85 if j in (1, 2) else 72
            cv.capsule((dx, y0 + 110, 0), (dx * 1.15, y0 + 110 + ln, 6), 17, 13, m)
        cv.capsule((-62, y0 + 50, 4), (-104, y0 + 104, 8), 18, 14, m)
        cv.capsule((0, y0 - 10, -10), (0, y0 - 40, -10), 40, 34, m)
        img, origin = cv.shade()
        frames.append((img, (int(origin[0]), int(origin[1]))))
    c1 = [None if 360 - 330 * min(1.0, (t / (n - 1)) * 1.4) > 120 else (-110, -200, 110, 0) for t in range(n)]
    return dict(frames=frames, t=3, loop=None, trans="add", clsn1=None, clsn1_frames=c1)


def wind_sword(n=4):
    frames = []
    m = Mat((0.7, 0.95, 0.9), spec=0.6, outline=0.5, rim=0.5, emissive=0.3)
    g = Mat((0.95, 0.95, 0.75), spec=0.6, outline=0.5)
    for t in range(n):
        cv = Canvas(xmin=-50, xmax=50, ymin=-10, ymax=210)
        cv.slab((0, 70, 0), 90, 70, 6, 3, m, bevel=2)
        cv.slab((0, 146, 1), 0, 16, 4, 3, g)
        cv.capsule((0, 150, 0), (0, 180, 0), 4, 4, g)
        for j in range(4):
            yy = 160 + j * 12 + t * 3
            cv.capsule((-12 + j * 8, yy, -4), (-14 + j * 8, yy + 30, -4), 2, 0.5, Mat((0.6, 0.9, 0.85), outline=0.8))
        img, origin = cv.shade()
        frames.append((img, (int(origin[0]), int(origin[1]))))
    return dict(frames=frames, t=2, loop=0, trans="add", clsn1=(-14, -150, 14, 0))


def pill_glow(n=8):
    frames = []
    for t in range(n):
        w = h = 70
        X, Y = grid(w, h, 35, 35)
        d = np.sqrt(X * X + Y * Y) / 30
        v = np.clip(1 - d, 0, 1) * 1.5
        th = np.arctan2(Y, X)
        rays = (np.abs(np.sin(th * 4 + t * 0.6)) > 0.93) * np.clip(1.2 - d, 0, 1)
        v = np.maximum(v, rays)
        core = (np.sqrt(X * X + Y * Y) < 6)
        rgb = ramp(FIRE_GOLD, v)
        rgb[core] = (0.95, 0.65, 0.2)
        frames.append((to_rgba(rgb, (v > 0.12) | core), (35, 35)))
    return dict(frames=frames, t=3, loop=0, trans="add", clsn1=None)


def sparkles(stops, w=120, h=200, n=8, seed=53, count=26):
    rng = np.random.default_rng(seed)
    P = [(rng.uniform(-w / 2, w / 2), rng.uniform(-h, 0), rng.uniform(0.6, 1.4)) for _ in range(count)]
    frames = []
    for t in range(n):
        W, H = w + 20, h + 40
        X, Y = grid(W, H, W / 2, H - 10)
        v = np.zeros((H, W), np.float32)
        for (px, py, s) in P:
            yy = py - t * 6 * s
            d = np.sqrt((X - px) ** 2 + (Y - yy) ** 2)
            star = np.clip(1 - d / (4 * s), 0, 1) + (np.abs(X - px) < 1) * np.clip(1 - np.abs(Y - yy) / (9 * s), 0, 1) \
                + (np.abs(Y - yy) < 1) * np.clip(1 - np.abs(X - px) / (9 * s), 0, 1)
            v = np.maximum(v, star * (1 - t / n * 0.6))
        frames.append((to_rgba(ramp(stops, v), v > 0.2), (int(W / 2), int(H - 10))))
    return dict(frames=frames, t=3, loop=None, trans="add", clsn1=None)


def dust(n=6):
    frames = []
    for t in range(n):
        k = (t + 1) / n
        w, h = 120, 50
        X, Y = grid(w, h, 60, 44)
        nz = fbm(h, w, 8, 61 + t)
        d = np.sqrt((X / (55 * (0.4 + 0.6 * k))) ** 2 + ((Y + 10) / (22 * (0.5 + 0.5 * k))) ** 2)
        v = (1 - d) + (nz - 0.5) * 0.8 - k * 0.45
        frames.append((to_rgba(ramp(DUST, nz), v > 0.1), (60, 44)))
    return dict(frames=frames, t=3, loop=None, trans=None, clsn1=None)


def rain(stops, w=560, h=300, n=6, seed=59):
    """Poison Calamity: a looming miasma cloud dripping toxic rain."""
    W, H = w, h
    cx, cy = W / 2, H - 4
    rng = np.random.default_rng(seed)
    drops = [(rng.uniform(-w / 2, w / 2), rng.uniform(0, h), rng.uniform(14, 30)) for _ in range(70)]
    frames = []
    base = fbm(H + 80, W + 80, 30, seed)
    for t in range(n):
        X, Y = grid(W, H, cx, cy)
        yy = -Y / h
        nz = base[t * 6:t * 6 + H, t * 9:t * 9 + W]
        cloudv = (yy - 0.72) * 4 + (nz - 0.5) * 2.0
        v = np.zeros((H, W), np.float32)
        for (px, py, ln) in drops:
            yy0 = (py + t * 26) % (h * 0.8)
            m = (np.abs(X - px) < 1.5) & (-Y > h * 0.8 - yy0 - ln) & (-Y < h * 0.8 - yy0)
            v = np.maximum(v, m * 0.8)
        rgb = np.where((cloudv > 0)[..., None], ramp(POISON, np.clip(0.4 + (nz - 0.5) * 1.4, 0, 1)),
                       ramp(FIRE_VENOM, v * 0.7))
        frames.append((to_rgba(rgb, (cloudv > 0) | (v > 0.3)), (int(cx), int(cy))))
    return dict(frames=frames, t=4, loop=0, trans=None, clsn1=(-w // 2 + 20, -h + 40, w // 2 - 20, 0))


def glow(stops, r=70, n=6):
    frames = []
    for t in range(n):
        w = h = int(r * 2.2)
        X, Y = grid(w, h, w / 2, h / 2)
        d = np.sqrt(X * X + Y * Y) / (r * (0.6 + 0.4 * ((t % 3) / 2)))
        th = np.arctan2(Y, X)
        rays = (np.abs(np.sin(th * 6 + t)) > 0.9) * np.clip(1.3 - d, 0, 1)
        v = np.maximum(np.clip(1 - d, 0, 1) * 1.3, rays * 0.9)
        frames.append((to_rgba(ramp(stops, v), v > 0.12), (int(w / 2), int(h / 2))))
    return dict(frames=frames, t=2, loop=None, trans="add", clsn1=None)


def make_fx(key):
    """Effect animation table for one fighter: {anim_id: effect}."""
    E = {6000: dust(), }
    if key == "xiaoyan":
        E[6010] = glow(FIRE_GREEN)
        E[6020] = burst(FIRE_GREEN, r=40, n=7)
        E[6100] = burst(FIRE_ORANGE, r=32, n=6, ring=False, seed=101)
        E[6110] = wave(FIRE_GREEN)
        E[6111] = burst(FIRE_GREEN, r=70)
        E[6120] = column(FIRE_ORANGE, w=80, h=230, seed=103)
        E[6130] = aura(FIRE_GREEN)
        E[6140] = lotus(0.55)
        E[6141] = lotus(1.0, seed=27)
        E[6142] = big_explosion()
    elif key == "yaolao":
        E[6010] = glow(SOUL)
        E[6020] = burst(FIRE_WHITE, r=40, n=7)
        E[6200] = fireball(FIRE_WHITE)
        E[6201] = burst(FIRE_WHITE, r=60)
        E[6210] = ring(SOUL, r=110)
        E[6220] = pill_glow()
        E[6221] = sparkles([(0, (0, 0.1, 0)), (0.5, (0.3, 0.9, 0.4)), (1, (1, 1, 0.8))])
        E[6230] = beam(FIRE_WHITE)
        E[6240] = spectral_hand()
        E[6241] = ring(SOUL, r=200, n=10, seed=71)
        E[6250] = sparkles(SOUL, w=120, h=220, count=30)
    elif key == "xuner":
        E[6010] = glow(FIRE_GOLD)
        E[6020] = burst(FIRE_GOLD, r=40, n=7)
        E[6300] = seal(FIRE_GOLD)
        E[6301] = burst(FIRE_GOLD, r=60)
        E[6310] = column(FIRE_GOLD, w=90, h=220, seed=107)
        E[6320] = seal(FIRE_GOLD, r=110, seed=21)
        E[6330] = column(FIRE_GOLD, w=200, h=470, seed=109)
    elif key == "medusa":
        E[6010] = glow(FIRE_VENOM)
        E[6020] = burst(FIRE_VENOM, r=40, n=7)
        E[6400] = fireball(FIRE_VENOM, seed=5)
        E[6401] = burst(FIRE_VENOM, r=60)
        E[6410] = sphere_vortex(FIRE_VENOM)
        E[6420] = python_serpent()
        E[6430] = sphere_vortex(FIRE_VENOM, r=150, n=14, implode=True, seed=39)
    elif key == "yunyun":
        E[6010] = glow(WIND)
        E[6020] = burst(WIND, r=40, n=7)
        E[6500] = crescent(WIND)
        E[6501] = burst(WIND, r=55)
        E[6510] = tornado(WIND, w=90, h=200, seed=45)
        E[6520] = tornado(WIND)
        E[6530] = wind_sword()
    elif key == "fairydoctor":
        E[6010] = glow(FIRE_VENOM)
        E[6020] = burst(FIRE_VENOM, r=40, n=7)
        E[6600] = cloud(POISON)
        E[6601] = burst(FIRE_VENOM, r=55)
        E[6610] = cloud(POISON, w=200, h=70, seed=33)
        E[6620] = cloud(POISON, w=420, h=300, seed=35, puffy=1.4)
        E[6630] = rain(POISON)
    return E
