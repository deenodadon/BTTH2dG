#!/usr/bin/env python3
"""Build every game asset into ../game (characters, stages, select.def).

usage: python3 tools/build.py [char ...] [--stages] [--jobs N]
"""
import argparse
import colorsys
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import cnsgen  # noqa: E402
import fx as FX  # noqa: E402
import sfx  # noqa: E402
from designs import DESIGNS  # noqa: E402
from rig import P  # noqa: E402
from sffv2 import SffWriter  # noqa: E402
from build_util import quantize_set  # noqa: E402
from snd import write_snd, wav_bytes  # noqa: E402
from spritegen import (anim_table, render_pose, crop, hurt_boxes, attack_boxes, to_air_box,  # noqa: E402
                       pose_key)
from rig import resolve  # noqa: E402

GAME = os.path.join(ROOT, "game")
CUSTOM = os.path.join(ROOT, "sounds", "custom")
PROJ_ANIMS = {6110, 6200, 6300, 6400, 6500, 6600}


# ------------------------------------------------------------------------------------------
# palette helpers


def is_skin(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.0 <= h <= 0.14 and 0.06 <= s <= 0.45 and v > 0.55


def alt_palette(colors, mode):
    out = [colors[0]]
    for (r, g, b) in colors[1:]:
        if is_skin(r, g, b):
            out.append((r, g, b))
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if mode == "hue1":
            h = (h + 0.33) % 1
            if s < 0.15:
                s = min(1, s + 0.25)
        elif mode == "hue2":
            h = (h + 0.6) % 1
            if s < 0.15:
                s = min(1, s + 0.2)
        elif mode == "dark":
            s *= 0.4
            v = v * 0.55
        elif mode == "pale":
            s *= 0.35
            v = min(1, v * 0.85 + 0.3)
        elif mode == "gold":
            h = 0.11 if s > 0.1 else h
            s = max(s, 0.55) if v > 0.2 else s
        rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
        out.append((int(rr * 255), int(gg * 255), int(bb * 255)))
    return out


# ------------------------------------------------------------------------------------------
# AIR writer


def air_action(no, frames, loop=None, comment=""):
    """frames: list of dict(spr=(g,i), t, clsn2=[...], clsn1=[...], flag='')"""
    out = []
    if comment:
        out.append("; " + comment)
    out.append("[Begin Action %d]" % no)
    for i, f in enumerate(frames):
        if loop is not None and i == loop and loop > 0:
            out.append("Loopstart")
        c2 = f.get("clsn2") or []
        c1 = f.get("clsn1") or []
        if c2:
            out.append("Clsn2: %d" % len(c2))
            for j, b in enumerate(c2):
                out.append(" Clsn2[%d] = %d, %d, %d, %d" % ((j,) + tuple(b)))
        if c1:
            out.append("Clsn1: %d" % len(c1))
            for j, b in enumerate(c1):
                out.append(" Clsn1[%d] = %d, %d, %d, %d" % ((j,) + tuple(b)))
        line = "%d,%d, 0,0, %d" % (f["spr"][0], f["spr"][1], f["t"])
        if f.get("flag"):
            line += ", ," + f["flag"]
        out.append(line)
    out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------
# portraits


def portrait(d, size, sz, head_only):
    p = dict(DESIGNS_STANCE[d["name"]])
    p["sz"] = sz
    p["lean"] = 2
    p["head"] = -6
    img, (ox, oy), s = render_pose(p, d, bounds=(-260 * sz / 2, 260 * sz / 2, -20, 240 * sz))
    im = Image.fromarray(img)
    hc = s.Hc
    cx = ox + hc[0]
    cy = oy - hc[1]
    w, h = size
    if head_only:
        box = (cx - w / 2 + 1 * sz, cy - h / 2 + 1 * sz, cx + w / 2 + 1 * sz, cy + h / 2 + 1 * sz)
    else:
        box = (cx - w * 0.5, cy - h * 0.24, cx + w * 0.5, cy + h * 0.76)
    out = im.crop(tuple(int(round(v)) for v in box))
    bg = Image.new("RGBA", out.size, (0, 0, 0, 0))
    bg.alpha_composite(out)
    return np.asarray(bg)


DESIGNS_STANCE = {}


# ------------------------------------------------------------------------------------------
# character build


def build_character(key, preview=True):
    t0 = time.time()
    d = DESIGNS[key]
    import anims as A
    sty = A.Style(key, d)
    DESIGNS_STANCE[d["name"]] = sty.stance
    T = anim_table(key, d)
    E = FX.make_fx(key)
    outdir = os.path.join(GAME, "chars", key)
    os.makedirs(outdir, exist_ok=True)

    # ---- render body frames (dedupe identical poses)
    cache = {}
    body_imgs = []      # list of (rgba, axis)
    body_keys = []      # (group, index) of each unique image
    air_frames = {}
    for aid in sorted(T):
        anim = T[aid]
        frs = []
        for i, f in enumerate(anim["frames"]):
            pk = pose_key(f["pose"])
            if pk not in cache:
                img, origin, s = render_pose(f["pose"], d)
                cimg, axis = crop(img, origin)
                cache[pk] = (len(body_imgs), s)
                body_imgs.append((cimg, axis))
                body_keys.append((aid, i))
            idx, s = cache[pk]
            spr = body_keys[idx]
            c2 = [to_air_box(b) for b in hurt_boxes(s, d)] if f.get("hurt", True) else []
            c1 = []
            if f.get("atk"):
                c1 = [to_air_box(b) for b in attack_boxes(s, resolve(f["pose"], d), d, f["atk"])]
            frs.append(dict(spr=spr, t=f["t"], clsn2=c2, clsn1=c1))
        air_frames[aid] = (frs, anim.get("loop"))
    t1 = time.time()

    sff = SffWriter()
    colors, ind = quantize_set([im for im, _ in body_imgs])
    sff.add_palette(1, 1, colors)
    for i, mode in enumerate(("hue1", "hue2", "dark", "pale", "gold")):
        sff.add_palette(1, i + 2, alt_palette(colors, mode))
    for (g, n), (im, axis), px in zip(body_keys, body_imgs, ind):
        h, w = px.shape
        sff.add_sprite(g, n, w, h, axis[0], axis[1], px.tobytes(), 0)

    # ---- effects
    air_fx = {}
    for k, (aid, e) in enumerate(sorted(E.items())):
        frames = [im for im, _ in e["frames"]]
        cols, ind_e = quantize_set(frames, 255)
        pal_idx = sff.add_palette(2, k, cols)
        frs = []
        cl = e.get("clsn1")
        clf = e.get("clsn1_frames")
        for i, ((im, axis), px) in enumerate(zip(e["frames"], ind_e)):
            h, w = px.shape
            sff.add_sprite(aid, i, w, h, axis[0], axis[1], px.tobytes(), pal_idx)
            box = clf[i] if clf else cl
            c1 = [box] if box else []
            c2 = [box] if (box and aid in PROJ_ANIMS) else []
            frs.append(dict(spr=(aid, i), t=e["t"], clsn1=c1, clsn2=c2,
                            flag="A" if e.get("trans") == "add" else ""))
        air_fx[aid] = (frs, e.get("loop"))

    # ---- portraits
    for num, size, sz, head in ((0, (50, 50), 1.6, True), (1, (240, 280), 2.9, False)):
        im = portrait(d, size, sz, head)
        cols, (px,) = quantize_set([im], 255)
        pi = sff.add_palette(3, num, cols)
        sff.add_sprite(9000, num, px.shape[1], px.shape[0], 0, 0, px.tobytes(), pi)
    sff.write(os.path.join(outdir, key + ".sff"))

    # ---- AIR
    air = ["; %s - animations (generated by tools/build.py)" % d["name"], ""]
    for aid in sorted(air_frames):
        frs, loop = air_frames[aid]
        air.append(air_action(aid, frs, loop))
    air.append("; ---- effects ----")
    for aid in sorted(air_fx):
        frs, loop = air_fx[aid]
        air.append(air_action(aid, frs, loop))
    with open(os.path.join(outdir, key + ".air"), "w") as f:
        f.write("\n".join(air))

    # ---- sounds
    S = sfx.char_sounds(key)
    sounds = []
    for (g, n), (samples, desc) in sorted(S.items()):
        custom = os.path.join(CUSTOM, key, "%d_%d.wav" % (g, n))
        if os.path.exists(custom):
            data = open(custom, "rb").read()
        else:
            data = wav_bytes(samples)
        sounds.append(((g, n), data))
    write_snd(os.path.join(outdir, key + ".snd"), sounds)

    # ---- CNS / CMD / DEF
    cnsgen.DESIGN_FLAGS[key] = d
    cns, cmd = cnsgen.build_char(key, d["name"], T, E)
    with open(os.path.join(outdir, key + ".cns"), "w") as f:
        f.write(cns)
    with open(os.path.join(outdir, key + ".cmd"), "w") as f:
        f.write(cmd)
    with open(os.path.join(outdir, key + ".def"), "w") as f:
        f.write(cnsgen.def_file(key, d["name"]))
    # move list
    ml = ["%s - move list" % d["name"], "=" * 40, ""]
    ml += ["Default keys: A light punch | S heavy punch | Z light kick | X heavy kick",
           "             D special button | C super button | Enter taunt",
           "Throw: Forward or Back + S (close) | Run: Forward,Forward | Hop back: Back,Back | Air recovery: A+S",
           "", "%-38s %-30s %s" % ("Move", "Easy input (classic input)", ""), "-" * 100]
    for nm, inp, desc in cnsgen.MOVELIST[key]:
        ml.append("%-38s %-30s %s" % (nm, easy_input(inp), desc))
    with open(os.path.join(outdir, "movelist.txt"), "w") as f:
        f.write("\n".join(ml) + "\n")
    t2 = time.time()
    meta = dict(key=key, sprites=len(body_keys), fx=len(E), render_s=round(t1 - t0, 1), total_s=round(t2 - t0, 1),
                sounds={"%d,%d" % k: v[1] for k, v in S.items()})
    return meta


EASY_INPUTS = [("QCF, QCF + P", "C"), ("QCB, QCB + P", "Down + C"), ("F, D, DF + P", "Down + D"),
               ("D, D + P", "Down + D"), ("QCF + P", "D"), ("QCB + P", "Forward + D"), ("QCB + K", "Back + D")]


def easy_input(inp):
    """Movelist text: easy key (engine default keyboard) with the classic motion in brackets."""
    for classic, easy in EASY_INPUTS:
        if inp.startswith(classic):
            return "%s%s (%s)" % (easy, inp[len(classic):], classic)
    return inp


def write_select(chars, stages):
    lines = ["; Battle Through the Heavens 2.5D - character & stage select", "[Characters]"]
    home = {"xiaoyan": "xiaoclan", "xuner": "xiaoclan", "yaolao": "flamecave", "medusa": "tagoredesert",
            "yunyun": "yunlanpeak", "fairydoctor": "yunlanpeak"}
    for c in chars:
        lines.append("%s/%s.def, stages/%s.def" % (c, c, home.get(c, stages[0])))
    lines += ["", "[ExtraStages]"]
    for s in stages:
        lines.append("stages/%s.def" % s)
    lines += ["", "[Options]", "arcade.maxmatches = 6,0,0,0,0,0,0,0,0,0",
              "team.maxmatches = 4,0,0,0,0,0,0,0,0,0", ""]
    os.makedirs(os.path.join(GAME, "data"), exist_ok=True)
    with open(os.path.join(GAME, "data", "select.def"), "w") as f:
        f.write("\n".join(lines))


def write_sound_slots(metas):
    os.makedirs(CUSTOM, exist_ok=True)
    out = ["# Sound slots", "",
           "Every sound is synthesised by `tools/sfx.py`. To use your own clips (for example ones you",
           "recorded yourself), save a WAV file as `sounds/custom/<character>/<group>_<index>.wav`",
           "and run `python3 tools/build.py <character>` again. Mono or stereo PCM WAV works best.", ""]
    for m in metas:
        out.append("## %s" % m["key"])
        out.append("")
        out.append("| file | used for |")
        out.append("|---|---|")
        for k, v in sorted(m["sounds"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split(","))):
            g, n = k.split(",")
            out.append("| `%s/%s_%s.wav` | %s |" % (m["key"], g, n, v))
        out.append("")
    with open(os.path.join(ROOT, "sounds", "SLOTS.md"), "w") as f:
        f.write("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chars", nargs="*")
    ap.add_argument("--stages", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    chars = a.chars or list(DESIGNS)
    import stages as STG
    if a.stages or not a.chars:
        STG.build_all(os.path.join(GAME, "stages"))
    with Pool(min(a.jobs, len(chars))) as pool:
        metas = pool.map(build_character, chars)
    for m in metas:
        print("%-12s sprites=%-4d fx=%-3d render=%ss total=%ss" % (m["key"], m["sprites"], m["fx"], m["render_s"],
                                                                     m["total_s"]))
    allchars = list(DESIGNS)
    write_select(allchars, STG.STAGE_IDS)
    prev = os.path.join(ROOT, "sounds", "slots.json")
    allmeta = {}
    if os.path.exists(prev):
        allmeta = json.load(open(prev))
    for m in metas:
        allmeta[m["key"]] = m["sounds"]
    os.makedirs(os.path.dirname(prev), exist_ok=True)
    json.dump(allmeta, open(prev, "w"), indent=1, sort_keys=True)
    write_sound_slots([dict(key=k, sounds=v) for k, v in allmeta.items() if k in DESIGNS])


if __name__ == "__main__":
    main()
