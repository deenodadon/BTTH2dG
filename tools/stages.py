"""Procedurally painted 2.5D stages: layered parallax backgrounds with a perspective floor."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fx import fbm, value_noise
from sffv2 import SffWriter
from build_util import quantize_rgba

STAGE_IDS = ["xiaoclan", "tagoredesert", "yunlanpeak", "flamecave"]

W = 1800  # layer width (wider than the camera travel so nothing runs out)


def grad(h, w, stops):
    ys = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, w, 3), np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (ys >= p0) & (ys <= p1)
        k = np.clip((ys - p0) / max(p1 - p0, 1e-6), 0, 1)
        col = np.array(c0)[None, None, :] * (1 - k[..., None]) + np.array(c1)[None, None, :] * k[..., None]
        out = np.where(m[..., None], np.broadcast_to(col, out.shape), out)
    return out


def rgba(rgb, alpha=None):
    h, w = rgb.shape[:2]
    a = np.full((h, w), 255, np.uint8) if alpha is None else np.where(alpha, 255, 0).astype(np.uint8)
    return np.dstack([np.clip(rgb * 255, 0, 255).astype(np.uint8), a])


def ridge(w, base, amp, cell, seed, sharp=False):
    n = fbm(1, w + 64, cell, seed, oct=5)[0, :w]
    if sharp:
        n = 1 - np.abs(n * 2 - 1)
    return base - amp * n


def mountains(h, w, color_top, color_bot, base, amp, cell, seed, snow=None, sharp=True, mist=0.0):
    """silhouette layer: returns rgba"""
    top = ridge(w, base, amp, cell, seed, sharp)
    ys = np.arange(h)[:, None]
    mask = ys >= top[None, :]
    k = np.clip((ys - top[None, :]) / max(amp, 1), 0, 1)
    col = np.array(color_top)[None, None] * (1 - k[..., None]) + np.array(color_bot)[None, None] * k[..., None]
    tex = fbm(h, w, 12, seed + 3)[..., None]
    col = col * (0.88 + 0.24 * tex)
    if snow:
        sm = mask & ((ys - top[None, :]) < 12 + 18 * fbm(h, w, 6, seed + 9))
        col[sm] = np.array(snow)
    if mist:
        col = col * (1 - mist * k[..., None]) + np.array(color_bot) * mist * k[..., None]
    return rgba(col, mask)


def draw_roof(dr, cx, y, wid, hgt, col, eave=None, tiles=None):
    """Chinese hip roof with upturned eaves."""
    eave = eave or wid * 0.18
    pts = [(cx - wid / 2 - eave, y - hgt * 0.15), (cx - wid / 2, y), (cx + wid / 2, y), (cx + wid / 2 + eave, y - hgt * 0.15),
           (cx + wid * 0.3, y - hgt * 0.85), (cx - wid * 0.3, y - hgt * 0.85)]
    dr.polygon(pts, fill=col)
    ridge_col = tuple(max(0, int(c * 0.6)) for c in col[:3]) + (255,)
    dr.line([(cx - wid * 0.32, y - hgt * 0.87), (cx + wid * 0.32, y - hgt * 0.87)], fill=ridge_col, width=max(2, int(hgt * 0.1)))
    if tiles:
        for i in range(int(wid / 7)):
            x = cx - wid / 2 + i * 7 + 3
            dr.line([(x, y - 1), (x + (x - cx) * 0.05, y - hgt * 0.8)], fill=tiles, width=1)
    dr.line([(cx - wid / 2 - eave, y - hgt * 0.15), (cx + wid / 2 + eave, y - hgt * 0.15)], fill=ridge_col, width=2)


def building(dr, cx, base_y, wid, hgt, wall, pillar, roof, tiles=None, floors=1, win=None):
    for f in range(floors):
        w = wid * (1 - 0.18 * f)
        h = hgt / floors
        y1 = base_y - f * (h + h * 0.35)
        y0 = y1 - h
        dr.rectangle([cx - w / 2, y0, cx + w / 2, y1], fill=wall)
        n = max(2, int(w / 40))
        for i in range(n + 1):
            x = cx - w / 2 + i * w / n
            dr.rectangle([x - 3, y0, x + 3, y1], fill=pillar)
        if win:
            for i in range(n):
                x = cx - w / 2 + (i + 0.5) * w / n
                dr.rectangle([x - w / n * 0.28, y0 + h * 0.2, x + w / n * 0.28, y0 + h * 0.65], fill=win)
        draw_roof(dr, cx, y0 + 2, w * 1.05, h * 0.55, roof, tiles=tiles)


def floor_tiles(h, w, c1, c2, line, seed, tile=48):
    """flat floor texture, later shown through a 'parallax' BG to get perspective."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    n = fbm(h, w, 10, seed)
    row = (ys // (h / 3)).astype(int)
    xo = xs + (row % 2) * tile / 2
    k = ((xo // tile).astype(int) + row) % 2
    col = np.where(k[..., None] == 0, np.array(c1), np.array(c2)) * (0.85 + 0.3 * n[..., None])
    grout = ((xo % tile) < 2) | ((ys % (h / 3)) < 1.5)
    col[grout] = np.array(line)
    shade = np.linspace(0.85, 1.1, h)[:, None, None]
    return rgba(np.clip(col * shade, 0, 1))


# ---------------------------------------------------------------------------------------------
# individual stages


def stage_xiaoclan():
    L = {}
    sky = grad(300, 640, [(0, (0.33, 0.55, 0.85)), (0.7, (0.75, 0.86, 0.96)), (1, (0.98, 0.92, 0.85))])
    cl = fbm(300, 640, 60, 3)
    clouds = np.clip((cl - 0.55) * 4, 0, 1)[..., None] * np.clip(1 - np.linspace(0, 1, 300)[:, None, None] * 1.3, 0, 1)
    L["sky"] = rgba(sky * (1 - clouds) + clouds * 0.98)
    L["far"] = mountains(220, W, (0.5, 0.6, 0.78), (0.72, 0.8, 0.9), 120, 100, 160, 11, snow=(0.92, 0.95, 1.0))
    L["mid"] = mountains(200, W, (0.32, 0.46, 0.42), (0.55, 0.66, 0.66), 110, 70, 90, 12, sharp=False, mist=0.4)
    # city roofs
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rng = np.random.default_rng(5)
    x = 20
    while x < W - 40:
        wid = rng.uniform(70, 140)
        hgt = rng.uniform(50, 90)
        building(dr, x + wid / 2, 200, wid, hgt, (150, 120, 105, 255), (110, 40, 35, 255), (70, 75, 95, 255),
                 floors=1 if rng.random() < 0.7 else 2)
        x += wid + rng.uniform(5, 40)
    # pagoda
    building(dr, 1300, 200, 120, 260, (160, 125, 105, 255), (130, 40, 35, 255), (60, 70, 92, 255), floors=4)
    L["city"] = np.asarray(im)
    # courtyard wall with gate & pavilion
    im = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 150, W, 260], fill=(205, 190, 170, 255))
    for i in range(0, W, 60):
        dr.rectangle([i, 150, i + 4, 260], fill=(170, 150, 130, 255))
    dr.rectangle([0, 140, W, 152], fill=(80, 85, 100, 255))
    for i in range(0, W, 14):
        dr.polygon([(i, 140), (i + 7, 132), (i + 14, 140)], fill=(70, 75, 92, 255))
    building(dr, W / 2, 255, 300, 180, (170, 45, 40, 255), (120, 25, 25, 255), (55, 62, 82, 255),
             tiles=(80, 88, 110, 255), win=(235, 205, 140, 255))
    dr.rectangle([W / 2 - 60, 110, W / 2 + 60, 140], fill=(40, 30, 20, 255))
    dr.rectangle([W / 2 - 56, 114, W / 2 + 56, 136], fill=(200, 160, 60, 255))
    for i, (bx, h) in enumerate(((260, 120), (1540, 120))):
        building(dr, bx, 255, 160, h, (175, 50, 45, 255), (120, 25, 25, 255), (55, 62, 82, 255),
                 tiles=(80, 88, 110, 255), win=(235, 205, 140, 255))
    # trees
    for tx in (520, 1240, 80, 1720):
        dr.rectangle([tx - 5, 140, tx + 5, 255], fill=(80, 55, 40, 255))
        for k in range(14):
            ax = tx + rng.uniform(-50, 50)
            ay = 120 + rng.uniform(-50, 30)
            r = rng.uniform(18, 32)
            dr.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(int(60 + rng.uniform(0, 40)), int(110 + rng.uniform(0, 50)), 70, 255))
    L["wall"] = np.asarray(im)
    L["floor"] = floor_tiles(70, 640, (0.62, 0.6, 0.58), (0.55, 0.53, 0.52), (0.35, 0.33, 0.33), 21)
    # foreground lantern post
    im = Image.new("RGBA", (120, 300), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rectangle([54, 0, 64, 300], fill=(60, 30, 25, 255))
    dr.rectangle([20, 20, 100, 30], fill=(60, 30, 25, 255))
    L["fg_post"] = np.asarray(im)
    # lantern animation frames
    L["lantern"] = []
    for f in range(4):
        im = Image.new("RGBA", (50, 70), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        g = 210 + f * 10
        dr.rectangle([22, 0, 28, 8], fill=(60, 30, 25, 255))
        dr.ellipse([3, 8, 47, 62], fill=(min(255, g + 20), int(g * 0.25), 30, 255))
        dr.ellipse([12, 14, 38, 56], fill=(255, min(255, 140 + f * 20), 80, 255))
        dr.rectangle([15, 60, 35, 66], fill=(200, 160, 60, 255))
        L["lantern"].append(np.asarray(im))
    # falling petals
    L["petals"] = petals(((245, 175, 190), (250, 205, 215), (230, 140, 160)))
    bgdef = [
        dict(name="sky", spr=(0, 0), start=(0, -60), delta=(0.05, 0.05), tile=(1, 0)),
        dict(name="clouds drift", spr=(0, 0), start=(0, -60), delta=(0.08, 0.05), tile=(1, 0), velocity=(0.15, 0),
             trans="add", alpha=None, skip=True),
        dict(name="far mountains", spr=(1, 0), start=(0, 70), delta=(0.12, 0.1), tile=(1, 0)),
        dict(name="hills", spr=(2, 0), start=(0, 110), delta=(0.22, 0.15), tile=(1, 0)),
        dict(name="city", spr=(3, 0), start=(0, 170), delta=(0.4, 0.3), tile=(1, 0)),
        dict(name="courtyard", spr=(4, 0), start=(0, 160), delta=(0.7, 0.6)),
        dict(name="floor", spr=(5, 0), start=(0, 410), delta=(0.78, 1), tile=(1, 0), parallax=True,
             xscale=(1, 1.28), yscalestart=100, yscaledelta=1.2),
        dict(name="lantern L", spr=None, anim=10, start=(-330, 300), delta=(0.7, 0.6)),
        dict(name="lantern R", spr=None, anim=10, start=(330, 300), delta=(0.7, 0.6)),
        dict(name="petals", spr=None, anim=11, start=(0, 0), delta=(1.1, 1), tile=(1, 1), velocity=(-0.4, 0.8),
             layer=1),
        dict(name="post L", spr=(7, 0), start=(-520, 180), delta=(1.35, 1), layer=1),
        dict(name="post R", spr=(7, 0), start=(560, 180), delta=(1.35, 1), layer=1),
    ]
    sprites = [((0, 0), L["sky"], (320, 0)), ((1, 0), L["far"], (W // 2, 0)), ((2, 0), L["mid"], (W // 2, 0)),
               ((3, 0), L["city"], (W // 2, 0)), ((4, 0), L["wall"], (W // 2, 0)),
               ((5, 0), L["floor"], (320, 0)), ((7, 0), L["fg_post"], (60, 0))]
    anims = {10: [((10, i), fr, (25, 0)) for i, fr in enumerate(L["lantern"])],
             11: [((11, i), fr, (0, 0)) for i, fr in enumerate(L["petals"])]}
    info = dict(name="Xiao Clan Courtyard", zoffset=420, shadow=(30, 30, 50), music="")
    return sprites, anims, bgdef, info


def petals(cols, n=4, w=640, h=480, count=40, seed=7):
    rng = np.random.default_rng(seed)
    P = [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, 6.28), cols[rng.integers(len(cols))]) for _ in range(count)]
    frames = []
    for f in range(n):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        for x, y, ph, c in P:
            a = ph + f * 0.8
            rx, ry = 4 * abs(math.cos(a)) + 1.5, 2.5
            dr.ellipse([x - rx, y - ry, x + rx, y + ry], fill=c + (255,))
        frames.append(np.asarray(im))
    return frames


def stage_tagore():
    L = {}
    sky = grad(300, 640, [(0, (0.25, 0.12, 0.35)), (0.45, (0.85, 0.35, 0.3)), (0.8, (1.0, 0.68, 0.35)),
                          (1, (1.0, 0.85, 0.55))])
    yy, xx = np.mgrid[0:300, 0:640]
    sun = np.clip(1 - np.sqrt((xx - 420) ** 2 + (yy - 215) ** 2) / 60, 0, 1)
    sky = sky + sun[..., None] * np.array([0.6, 0.45, 0.2])
    L["sky"] = rgba(np.clip(sky, 0, 1))
    L["far"] = mountains(200, W, (0.55, 0.3, 0.32), (0.85, 0.5, 0.38), 140, 50, 220, 31, sharp=False, mist=0.5)
    L["dunes"] = mountains(200, W, (0.88, 0.58, 0.32), (0.75, 0.45, 0.25), 90, 60, 140, 32, sharp=False)
    # ruins: sandstone columns & snake statues
    im = Image.new("RGBA", (W, 280), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rng = np.random.default_rng(9)
    for i in range(14):
        x = 60 + i * 125 + rng.uniform(-20, 20)
        h = rng.uniform(90, 220)
        broken = rng.random() < 0.5
        dr.rectangle([x - 16, 280 - h, x + 16, 280], fill=(196, 140, 92, 255))
        for k in range(int(h / 18)):
            dr.line([(x - 16, 280 - k * 18), (x + 16, 280 - k * 18)], fill=(150, 100, 65, 255), width=2)
        dr.rectangle([x - 22, 280 - h - 10, x + 22, 280 - h], fill=(176, 120, 78, 255))
        if broken:
            dr.polygon([(x - 22, 280 - h - 10), (x + 4, 280 - h - 26), (x + 22, 280 - h - 10)], fill=(176, 120, 78, 255))
    for x in (500, 1300):
        # cobra statue
        dr.rectangle([x - 50, 230, x + 50, 280], fill=(150, 105, 70, 255))
        dr.polygon([(x - 18, 230), (x - 30, 120), (x - 60, 80), (x - 30, 40), (x, 30), (x + 30, 40), (x + 60, 80),
                    (x + 30, 120), (x + 18, 230)], fill=(120, 90, 70, 255))
        dr.ellipse([x - 14, 52, x - 4, 60], fill=(240, 200, 60, 255))
        dr.ellipse([x + 4, 52, x + 14, 60], fill=(240, 200, 60, 255))
    L["ruins"] = np.asarray(im)
    sand = fbm(70, 640, 14, 33)
    ys, xs = np.mgrid[0:70, 0:640]
    rip = np.sin(xs * 0.08 + sand * 8 + ys * 0.3) * 0.5 + 0.5
    col = np.array([0.9, 0.66, 0.4])[None, None] * (0.8 + 0.2 * rip[..., None]) * (0.85 + 0.25 * sand[..., None])
    L["floor"] = rgba(np.clip(col, 0, 1))
    L["haze"] = petals(((240, 200, 150), (230, 180, 120)), count=22, seed=11)
    im = Image.new("RGBA", (140, 320), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.polygon([(20, 320), (30, 60), (70, 10), (110, 70), (120, 320)], fill=(120, 80, 55, 255))
    for k in range(10):
        dr.line([(25, 320 - k * 28), (118, 320 - k * 28)], fill=(90, 60, 40, 255), width=3)
    L["fg"] = np.asarray(im)
    bgdef = [
        dict(name="sky", spr=(0, 0), start=(0, -60), delta=(0.05, 0.05), tile=(1, 0)),
        dict(name="far", spr=(1, 0), start=(0, 120), delta=(0.12, 0.1), tile=(1, 0)),
        dict(name="dunes", spr=(2, 0), start=(0, 200), delta=(0.3, 0.25), tile=(1, 0)),
        dict(name="ruins", spr=(3, 0), start=(0, 140), delta=(0.65, 0.6)),
        dict(name="floor", spr=(5, 0), start=(0, 410), delta=(0.78, 1), tile=(1, 0), parallax=True,
             xscale=(1, 1.28), yscalestart=100, yscaledelta=1.2),
        dict(name="sand drift", spr=None, anim=11, start=(0, 0), delta=(1.1, 1), tile=(1, 1), velocity=(-2.2, 0.3),
             layer=1),
        dict(name="fg pillar", spr=(7, 0), start=(560, 170), delta=(1.4, 1), layer=1),
    ]
    sprites = [((0, 0), L["sky"], (320, 0)), ((1, 0), L["far"], (W // 2, 0)), ((2, 0), L["dunes"], (W // 2, 0)),
               ((3, 0), L["ruins"], (W // 2, 0)), ((5, 0), L["floor"], (320, 0)), ((7, 0), L["fg"], (70, 0))]
    anims = {11: [((11, i), fr, (0, 0)) for i, fr in enumerate(L["haze"])]}
    info = dict(name="Tagore Desert Ruins", zoffset=420, shadow=(60, 30, 20), music="")
    return sprites, anims, bgdef, info


def stage_yunlan():
    L = {}
    sky = grad(300, 640, [(0, (0.2, 0.4, 0.8)), (0.6, (0.55, 0.75, 0.95)), (1, (0.9, 0.95, 1.0))])
    L["sky"] = rgba(sky)
    L["peaks"] = mountains(260, W, (0.35, 0.45, 0.55), (0.75, 0.82, 0.9), 200, 180, 120, 41, snow=(0.95, 0.97, 1.0),
                           mist=0.5)
    # cloud sea frames (scrolling via velocity)
    cl = fbm(160, 640, 40, 43)
    a = np.clip((cl - 0.35) * 3 + np.linspace(-0.4, 0.8, 160)[:, None], 0, 1)
    col = np.dstack([0.85 + 0.15 * a, 0.9 + 0.1 * a, 0.97 + 0.03 * a])
    L["clouds"] = rgba(col, a > 0.35)
    # mountain-top temple and pines
    im = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.polygon([(0, 300), (0, 220), (300, 200), (700, 160), (W / 2, 150), (1100, 160), (1500, 200), (W, 220), (W, 300)],
               fill=(110, 120, 115, 255))
    building(dr, W / 2, 170, 260, 150, (240, 240, 245, 255), (90, 120, 170, 255), (50, 80, 120, 255),
             tiles=(70, 100, 140, 255), floors=2, win=(180, 210, 240, 255))
    building(dr, 500, 205, 140, 90, (240, 240, 245, 255), (90, 120, 170, 255), (50, 80, 120, 255))
    building(dr, 1300, 205, 140, 90, (240, 240, 245, 255), (90, 120, 170, 255), (50, 80, 120, 255))
    rng = np.random.default_rng(3)
    for tx in (120, 300, 760, 1050, 1500, 1700):
        ty = 230
        dr.line([(tx, ty + 60), (tx + rng.uniform(-10, 10), ty - 40)], fill=(70, 50, 40, 255), width=6)
        for k in range(5):
            yy = ty - 40 + k * 18
            ww = 30 + k * 10
            dr.polygon([(tx - ww, yy + 12), (tx, yy - 10), (tx + ww, yy + 12)], fill=(40, 90 + k * 6, 60, 255))
    L["temple"] = np.asarray(im)
    L["floor"] = floor_tiles(70, 640, (0.9, 0.9, 0.92), (0.82, 0.83, 0.87), (0.6, 0.62, 0.68), 45, tile=64)
    # railing foreground
    im = Image.new("RGBA", (640, 60), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 10, 640, 18], fill=(235, 235, 240, 255))
    for x in range(0, 640, 40):
        dr.rectangle([x + 2, 10, x + 10, 60], fill=(225, 225, 232, 255))
        dr.rectangle([x, 4, x + 12, 12], fill=(210, 210, 220, 255))
    L["rail"] = np.asarray(im)
    L["wind"] = petals(((255, 255, 255), (220, 240, 235)), count=50, seed=13)
    bgdef = [
        dict(name="sky", spr=(0, 0), start=(0, -60), delta=(0.03, 0.05), tile=(1, 0)),
        dict(name="peaks", spr=(1, 0), start=(0, 40), delta=(0.12, 0.1), tile=(1, 0)),
        dict(name="cloud sea", spr=(2, 0), start=(0, 210), delta=(0.25, 0.2), tile=(1, 0), velocity=(-0.3, 0)),
        dict(name="temple", spr=(3, 0), start=(0, 115), delta=(0.6, 0.55)),
        dict(name="floor", spr=(5, 0), start=(0, 410), delta=(0.78, 1), tile=(1, 0), parallax=True,
             xscale=(1, 1.28), yscalestart=100, yscaledelta=1.2),
        dict(name="wind motes", spr=None, anim=11, start=(0, 0), delta=(1.1, 1), tile=(1, 1), velocity=(-1.6, 0.2),
             layer=1),
        dict(name="railing", spr=(7, 0), start=(0, 436), delta=(1.3, 1), tile=(1, 0), layer=1),
    ]
    sprites = [((0, 0), L["sky"], (320, 0)), ((1, 0), L["peaks"], (W // 2, 0)), ((2, 0), L["clouds"], (320, 0)),
               ((3, 0), L["temple"], (W // 2, 0)), ((5, 0), L["floor"], (320, 0)), ((7, 0), L["rail"], (320, 0))]
    anims = {11: [((11, i), fr, (0, 0)) for i, fr in enumerate(L["wind"])]}
    info = dict(name="Yun Lan Sect Peak", zoffset=420, shadow=(40, 50, 80), music="")
    return sprites, anims, bgdef, info


def stage_cave():
    L = {}
    bg = grad(300, 640, [(0, (0.05, 0.02, 0.04)), (0.6, (0.22, 0.06, 0.04)), (1, (0.55, 0.15, 0.05))])
    L["sky"] = rgba(bg)
    rock = mountains(300, W, (0.2, 0.1, 0.1), (0.4, 0.14, 0.08), 160, 140, 70, 51, sharp=True)
    L["rock"] = rock
    # stalactites
    im = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rng = np.random.default_rng(4)
    dr.rectangle([0, 0, W, 30], fill=(35, 18, 18, 255))
    for i in range(70):
        x = rng.uniform(0, W)
        w = rng.uniform(10, 40)
        h = rng.uniform(30, 150)
        dr.polygon([(x - w, 20), (x, h), (x + w, 20)], fill=(int(40 + rng.uniform(0, 20)), 20, 20, 255))
    L["ceiling"] = np.asarray(im)
    # lava floor with glowing cracks
    n = fbm(70, 640, 12, 55)
    cracks = np.abs(fbm(70, 640, 20, 57) - 0.5) < 0.035
    col = np.dstack([0.25 + 0.15 * n, 0.12 + 0.05 * n, 0.1 + 0.03 * n])
    col[cracks] = (1.0, 0.55, 0.1)
    L["floor"] = rgba(col)
    # flame orbs (heavenly flames floating)
    L["orbs"] = []
    from fx import flame_field, ramp, FIRE_ORANGE, FIRE_GREEN
    for f in range(6):
        im = np.zeros((90, 70, 4), np.uint8)

        def shape(X, Y):
            return np.clip(1 - np.sqrt((X / 22) ** 2 + ((Y - 6) / 30) ** 2), 0, 1) * 1.7
        v = flame_field(70, 90, 35, 55, shape, f, 61, cell=10, speed=10)
        cols = ramp(FIRE_GREEN if True else FIRE_ORANGE, v)
        im[..., :3] = (cols * 255).astype(np.uint8)
        im[..., 3] = np.where(v > 0.2, 255, 0)
        L["orbs"].append(im)
    L["embers"] = petals(((255, 160, 60), (255, 220, 120), (255, 90, 30)), count=50, seed=17)
    bgdef = [
        dict(name="glow", spr=(0, 0), start=(0, -60), delta=(0.05, 0.05), tile=(1, 0)),
        dict(name="far rock", spr=(1, 0), start=(0, 110), delta=(0.25, 0.2), tile=(1, 0)),
        dict(name="flame orb 1", spr=None, anim=10, start=(-260, 200), delta=(0.4, 0.3), trans="add"),
        dict(name="flame orb 2", spr=None, anim=10, start=(300, 170), delta=(0.4, 0.3), trans="add"),
        dict(name="ceiling", spr=(2, 0), start=(0, -60), delta=(0.6, 0.5), tile=(1, 0)),
        dict(name="floor", spr=(5, 0), start=(0, 410), delta=(0.78, 1), tile=(1, 0), parallax=True,
             xscale=(1, 1.28), yscalestart=100, yscaledelta=1.2),
        dict(name="embers", spr=None, anim=11, start=(0, 0), delta=(1.1, 1), tile=(1, 1), velocity=(0.3, -1.2),
             layer=1, trans="add"),
    ]
    sprites = [((0, 0), L["sky"], (320, 0)), ((1, 0), L["rock"], (W // 2, 0)), ((2, 0), L["ceiling"], (W // 2, 0)),
               ((5, 0), L["floor"], (320, 0))]
    anims = {10: [((10, i), fr, (35, 45)) for i, fr in enumerate(L["orbs"])],
             11: [((11, i), fr, (0, 0)) for i, fr in enumerate(L["embers"])]}
    info = dict(name="Heavenly Flame Cavern", zoffset=420, shadow=(20, 0, 0), music="")
    return sprites, anims, bgdef, info


STAGES = {"xiaoclan": stage_xiaoclan, "tagoredesert": stage_tagore, "yunlanpeak": stage_yunlan,
          "flamecave": stage_cave}


def write_stage(sid, outdir):
    sprites, anims, bgdef, info = STAGES[sid]()
    sff = SffWriter()
    k = 0
    for (g, n), im, axis in sprites:
        cols, px = quantize_rgba([im])
        pi = sff.add_palette(1, k, cols)
        k += 1
        sff.add_sprite(g, n, px[0].shape[1], px[0].shape[0], axis[0], axis[1], px[0].tobytes(), pi)
    for aid, frs in anims.items():
        cols, pxs = quantize_rgba([im for _, im, _ in frs])
        pi = sff.add_palette(1, k, cols)
        k += 1
        for ((g, n), im, axis), px in zip(frs, pxs):
            sff.add_sprite(g, n, px.shape[1], px.shape[0], axis[0], axis[1], px.tobytes(), pi)
    os.makedirs(outdir, exist_ok=True)
    sff.write(os.path.join(outdir, sid + ".sff"))
    sc = info["shadow"]
    lines = ["; %s - Battle Through the Heavens 2.5D (fan-made)" % info["name"],
             "[Info]", 'name = "%s"' % info["name"], 'displayname = "%s"' % info["name"],
             'author = "BTTH 2.5D fan project"', "", "[Camera]", "startx = 0", "starty = 0",
             "boundleft = -420", "boundright = 420", "boundhigh = -60", "boundlow = 0", "verticalfollow = .2",
             "floortension = 40", "tension = 80", "", "[PlayerInfo]", "p1startx = -140", "p1starty = 0",
             "p1startz = 0", "p1facing = 1", "p2startx = 140", "p2starty = 0", "p2startz = 0", "p2facing = -1",
             "leftbound = -1000", "rightbound = 1000", "topbound = 0", "botbound = 0", "", "[Scaling]",
             "topz = 0", "botz = 50", "topscale = 1", "botscale = 1.2", "", "[Bound]", "screenleft = 15",
             "screenright = 15", "", "[StageInfo]", "zoffset = %d" % info["zoffset"], "autoturn = 1",
             "resetBG = 1", "localcoord = 640, 480", "xscale = 1", "yscale = 1", "", "[Shadow]",
             "intensity = 110", "color = %d, %d, %d" % sc, "yscale = .25", "fade.range = 0, 0", "",
             "[Reflection]", "intensity = 0", "", "[Music]",
             "; drop an mp3/ogg in sound/ and point bgmusic at it", "bgmusic = %s" % info["music"],
             "bgvolume = 0", "", "[BGdef]", "spr = %s.sff" % sid, "debugbg = 0", ""]
    for aid, frs in anims.items():
        lines.append("[Begin Action %d]" % aid)
        for (g, n), _, _ in frs:
            lines.append("%d,%d, 0,0, %d" % (g, n, 6 if aid == 10 else 5))
        lines.append("")
    for b in bgdef:
        if b.get("skip"):
            continue
        lines.append("[BG %s]" % b["name"])
        if b.get("parallax"):
            lines.append("type = parallax")
        elif b.get("anim") is not None:
            lines.append("type = anim")
            lines.append("actionno = %d" % b["anim"])
        else:
            lines.append("type = normal")
        if b.get("spr"):
            lines.append("spriteno = %d, %d" % b["spr"])
        lines.append("layerno = %d" % b.get("layer", 0))
        lines.append("start = %d, %d" % b["start"])
        lines.append("delta = %s, %s" % b["delta"])
        if b.get("tile"):
            lines.append("tile = %d, %d" % b["tile"])
        if b.get("velocity"):
            lines.append("velocity = %s, %s" % b["velocity"])
        if b.get("xscale"):
            lines.append("xscale = %s, %s" % b["xscale"])
            lines.append("yscalestart = %s" % b["yscalestart"])
            lines.append("yscaledelta = %s" % b["yscaledelta"])
        if b.get("trans"):
            lines.append("trans = %s" % b["trans"])
        lines.append("mask = 1")
        lines.append("")
    with open(os.path.join(outdir, sid + ".def"), "w") as f:
        f.write("\n".join(lines))


def build_all(outdir):
    for sid in STAGE_IDS:
        write_stage(sid, outdir)
