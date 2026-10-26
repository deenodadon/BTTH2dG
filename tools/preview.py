#!/usr/bin/env python3
"""Render preview images straight from the built game files (no engine needed).

  python3 tools/preview.py scene <stage> <p1> <p2> [anim1] [anim2] out.png
  python3 tools/preview.py gif <char> <anim> out.gif
  python3 tools/preview.py roster out.png
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sffv2 import read_sff  # noqa: E402
from lint import parse_air, ini_sections  # noqa: E402

_cache = {}


def load_sff(path):
    if path not in _cache:
        _cache[path] = read_sff(path)
    return _cache[path]


def sprite_rgba(path, g, n, pal_override=None):
    pals, spr = load_sff(path)
    s = spr[(g, n)]
    pal = pals[s["pal"]][1] if pal_override is None else pal_override
    idx = np.frombuffer(s["pixels"], np.uint8).reshape(s["h"], s["w"])
    lut = np.zeros((256, 4), np.uint8)
    for i, c in enumerate(pal[:256]):
        lut[i, :3] = c
        lut[i, 3] = 0 if i == 0 else 255
    return Image.fromarray(lut[idx]), (s["ax"], s["ay"])


def char_frame(key, anim, elem=0, palno=1):
    base = os.path.join(ROOT, "game", "chars", key)
    air = parse_air(open(os.path.join(base, key + ".air")).read(), key)
    g, n, t = air[anim][min(elem, len(air[anim]) - 1)]
    path = os.path.join(base, key + ".sff")
    pals, _ = load_sff(path)
    pal = None
    if palno != 1:
        pal = dict(pals)[(1, palno)]
    elif (g < 6000):
        pal = dict(pals)[(1, 1)]
    return sprite_rgba(path, g, n, pal)


def stage_image(sid, camx=0, W=640, H=480):
    base = os.path.join(ROOT, "game", "stages")
    text = open(os.path.join(base, sid + ".def")).read()
    sffp = os.path.join(base, sid + ".sff")
    air = parse_air(text, sid)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    fg = []
    for sec, items in ini_sections(text):
        if not sec.lower().startswith("bg ") or sec.lower() == "bgdef":
            continue
        d = {k: v for k, v, _ in items}
        if "spriteno" in d:
            g, n = [int(x) for x in d["spriteno"].split(",")]
        else:
            g, n, _ = air[int(d["actionno"])][0]
        im, (ax, ay) = sprite_rgba(sffp, g, n)
        sx, sy = [float(x) for x in d["start"].split(",")]
        dx = float(d.get("delta", "1,1").split(",")[0])
        tile = [int(x) for x in d.get("tile", "0,0").split(",")]
        layer = int(d.get("layerno", 0))
        x0 = W / 2 + sx - ax - camx * dx
        y0 = sy - ay
        tgt = canvas
        if layer == 1:
            tgt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fg.append(tgt)
        xs = [x0]
        if tile[0]:
            k = int(np.floor(x0 / im.width))
            xs = [x0 - (k + j) * im.width for j in range(-1, int(W / im.width) + 3)]
        ys = [y0]
        if tile[1]:
            ys = [y0 + j * im.height for j in range(-1, int(H / im.height) + 2)]
        if d.get("type") == "parallax":
            # approximate the perspective floor: stretch rows progressively
            arr = np.asarray(im)
            rows = []
            xsc = [float(v) for v in d.get("xscale", "1,1").split(",")]
            for r in range(arr.shape[0]):
                k = xsc[0] + (xsc[1] - xsc[0]) * r / max(arr.shape[0] - 1, 1)
                row = Image.fromarray(arr[r:r + 1]).resize((int(arr.shape[1] * k), 1))
                full = Image.new("RGBA", (W, 1))
                for x in range(-row.width, W + row.width, row.width):
                    full.paste(row, (x + int((W - row.width) / 2) % row.width - row.width, 0))
                rows.append(np.asarray(full))
            im = Image.fromarray(np.concatenate(rows, 0))
            xs = [0]
        for x in xs:
            for y in ys:
                if d.get("trans") == "add":
                    a = np.asarray(tgt).astype(np.int32)
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    lay.paste(im, (int(x), int(y)))
                    la = np.asarray(lay).astype(np.int32)
                    a[..., :3] = np.minimum(255, a[..., :3] + la[..., :3] * (la[..., 3:] > 0))
                    tgt.paste(Image.fromarray(a.astype(np.uint8)))
                else:
                    tgt.paste(im, (int(x), int(y)), im)
    return canvas, fg


def put(canvas, im, axis, x, y, flip=False):
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        axis = (im.width - axis[0], axis[1])
    canvas.paste(im, (int(x - axis[0]), int(y - axis[1])), im)


def shadow(canvas, im, axis, x, y, flip=False):
    a = np.asarray(im)[..., 3] > 0
    w = im.width
    sh = Image.new("RGBA", (w, max(2, int(im.height * 0.18))), (0, 0, 0, 0))
    m = Image.fromarray((a * 90).astype(np.uint8)).resize(sh.size)
    sh.putalpha(m)
    if flip:
        sh = sh.transpose(Image.FLIP_LEFT_RIGHT)
        axis = (w - axis[0], axis[1])
    canvas.alpha_composite(sh, (max(0, int(x - axis[0])), int(y - 2)))


def scene(sid, p1, p2, a1=0, a2=0, e1=0, e2=0, out=None, fx=None):
    W, H = 640, 480
    canvas, fg = stage_image(sid)
    ground = 420
    for key, anim, elem, x, flip, pal in ((p1, a1, e1, 220, False, 1), (p2, a2, e2, 420, True, 1)):
        im, ax = char_frame(key, anim, elem, pal)
        shadow(canvas, im, ax, x, ground, flip)
        put(canvas, im, ax, x, ground, flip)
    if fx:
        for key, anim, elem, x, y, flip in fx:
            im, ax = char_frame(key, anim, elem)
            arr = np.asarray(canvas).astype(np.int32)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            put(lay, im, ax, x, y, flip)
            la = np.asarray(lay).astype(np.int32)
            arr[..., :3] = np.minimum(255, arr[..., :3] + la[..., :3] * (la[..., 3:] > 0))
            canvas = Image.fromarray(arr.astype(np.uint8))
    for f in fg:
        canvas.alpha_composite(f)
    # simple life bars for the mock-up
    dr = ImageDraw.Draw(canvas)
    for i, x0 in enumerate((20, 345)):
        dr.rectangle([x0, 20, x0 + 275, 34], fill=(30, 20, 20, 255), outline=(240, 210, 120, 255))
        dr.rectangle([x0 + 2, 22, x0 + 273 - (60 if i else 20), 32], fill=(230, 180, 40, 255))
    if out:
        canvas.convert("RGB").save(out)
    return canvas


def gif(key, anim, out, scale=1):
    base = os.path.join(ROOT, "game", "chars", key)
    air = parse_air(open(os.path.join(base, key + ".air")).read(), key)
    frames = []
    durs = []
    imgs = [char_frame(key, anim, i) for i in range(len(air[anim]))]
    minx = min(-ax[0] for im, ax in imgs)
    maxx = max(im.width - ax[0] for im, ax in imgs)
    miny = min(-ax[1] for im, ax in imgs)
    maxy = max(im.height - ax[1] for im, ax in imgs)
    for (im, ax), (g, n, t) in zip(imgs, air[anim]):
        c = Image.new("RGBA", (maxx - minx + 20, maxy - miny + 20), (52, 58, 72, 255))
        put(c, im, ax, -minx + 10, -miny + 10)
        frames.append(c.convert("RGB").resize((c.width * scale, c.height * scale)))
        durs.append(max(t if t > 0 else 30, 2) * 1000 // 60)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0)


def roster(out):
    keys = ["xiaoyan", "yaolao", "xuner", "medusa", "yunyun", "fairydoctor"]
    tiles = []
    for k in keys:
        base = os.path.join(ROOT, "game", "chars", k)
        im, _ = sprite_rgba(os.path.join(base, k + ".sff"), 9000, 1)
        tiles.append(im)
    W = sum(t.width for t in tiles) + 10 * (len(tiles) + 1)
    H = max(t.height for t in tiles) + 20
    c = Image.new("RGBA", (W, H), (25, 20, 35, 255))
    x = 10
    for t in tiles:
        c.alpha_composite(t, (x, 10))
        x += t.width + 10
    c.convert("RGB").save(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "scene":
        sid, p1, p2 = sys.argv[2:5]
        a1, a2 = int(sys.argv[5]), int(sys.argv[6])
        scene(sid, p1, p2, a1, a2, out=sys.argv[7])
    elif cmd == "gif":
        gif(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif cmd == "roster":
        roster(sys.argv[2])
