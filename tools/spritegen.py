"""Turns animation definitions into rendered sprites, collision boxes and AIR data."""
import math

import numpy as np

import anims as A
from render3d import Canvas
from rig import build, resolve, skeleton, dvec
from specials import make_specials


def anim_table(key, d):
    sty = A.Style(key, d)
    T = {}
    T[0] = A.anim_idle(sty)
    T[5] = A.anim_turn(sty)
    T[6] = A.anim_turn(sty, crouch=True)
    T[10] = A.anim_crouch_trans(sty, True)
    T[11] = A.anim_crouch(sty)
    T[12] = A.anim_crouch_trans(sty, False)
    T[20] = A.anim_walk(sty)
    T[21] = A.anim_walk(sty, back=True)
    T[40] = A.anim_jumpstart(sty)
    T[41] = A.anim_jump(sty, "up")
    T[42] = A.anim_jump(sty, "fwd")
    T[43] = A.anim_jump(sty, "back")
    T[47] = A.anim_land(sty)
    T[100] = A.anim_run(sty)
    T[105] = A.anim_hopback(sty)
    T[120] = A.anim_guardstart(sty)
    T[121] = A.anim_guardstart(sty, crouch=True)
    T[122] = A.anim_guard(sty, air=True)
    T[130] = A.anim_guard(sty)
    T[131] = A.anim_guard(sty, crouch=True)
    T[132] = A.anim_guard(sty, air=True)
    T[140] = A.anim_guardstart(sty)
    T[141] = A.anim_guardstart(sty, crouch=True)
    T[142] = A.anim_guard(sty, air=True)
    T[150] = A.anim_guardhit(sty)
    T[151] = A.anim_guardhit(sty, crouch=True)
    T[152] = A.anim_guardhit(sty, air=True)
    T[170] = A.anim_lose(sty)
    T[175] = A.anim_lose(sty)
    T[180] = A.anim_win(sty)
    T[190] = A.anim_intro(sty)
    T[195] = A.anim_taunt(sty)
    T[200] = A.anim_lp(sty)
    T[210] = A.anim_hp(sty)
    T[230] = A.anim_lk(sty)
    T[240] = A.anim_hk(sty)
    T[400] = A.anim_clp(sty)
    T[410] = A.anim_chp(sty)
    T[430] = A.anim_clk(sty)
    T[440] = A.anim_chk(sty)
    T[600] = A.anim_jlp(sty)
    T[610] = A.anim_jhp(sty)
    T[630] = A.anim_jlk(sty)
    T[640] = A.anim_jhk(sty)
    T[800] = A.anim_throw_try(sty)
    T[810] = A.anim_throw(sty)
    for lvl in range(3):
        T[5000 + lvl] = A.anim_hit(sty, lvl, "high")
        T[5010 + lvl] = A.anim_hit(sty, lvl, "low")
        T[5020 + lvl] = A.anim_hit(sty, lvl, "crouch")
    T[5005] = A.anim_hit_recover(sty, "high")
    T[5015] = A.anim_hit_recover(sty, "low")
    T[5025] = A.anim_hit_recover(sty, "crouch")
    T[5030] = A.anim_air_hit(sty)
    T[5035] = A.anim_air_trans(sty)
    T[5040] = A.anim_air_up(sty)
    T[5050] = A.anim_fall(sty)
    T[5060] = A.anim_fall(sty)
    T[5070] = A.anim_trip(sty)
    T[5080] = A.anim_lie_hit(sty)
    T[5090] = A.anim_lie_hit(sty)
    T[5100] = A.anim_bounce(sty, hold=False)
    T[5101] = A.anim_bounce(sty)
    T[5110] = A.anim_lying(sty)
    T[5120] = A.anim_getup(sty)
    T[5140] = A.anim_lying(sty, dead=True)
    T[5150] = A.anim_lying(sty, dead=True)
    T[5160] = A.anim_bounce(sty)
    T[5170] = A.anim_bounce(sty, hold=False)
    T[5200] = A.anim_recover(sty, near_ground=True)
    T[5210] = A.anim_recover(sty)
    T[5300] = A.anim_dizzy(sty)
    T.update(make_specials(key, sty))
    return T


def pose_key(p):
    return tuple(sorted((k, round(v, 2) if isinstance(v, float) else v) for k, v in p.items()))


def render_pose(p, d, bounds=None):
    cv = Canvas(*bounds) if bounds else Canvas()
    s = build(cv, p, d)
    img, origin = cv.shade()
    return img, origin, s


def crop(img, origin):
    a = img[..., 3]
    ys, xs = np.nonzero(a)
    if len(xs) == 0:
        return np.zeros((1, 1, 4), np.uint8), (0, 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    ox, oy = origin
    return img[y0:y1, x0:x1], (int(round(ox - x0)), int(round(oy - y0)))


def _box(pts, pad):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def hurt_boxes(s, d):
    boxes = [_box([s.Hc], 14 * s.hs), _box([s.P, s.C, s.Nb], 16 * s.hs)]
    if d.get("lower") == "ghost":
        boxes.append(_box([s.P, s.P + 60 * s.hs * dvec(0)], 15 * s.hs))
    else:
        boxes.append(_box([s.Hp, s.Kn, s.Kf, s.An, s.Af], 8 * s.hs))
    return boxes


def attack_boxes(s, p, d, atk):
    out = []
    for a in atk:
        if isinstance(a, tuple) and a[0] == "box":
            out.append(a[1:])
        elif a in ("nhand", "fhand"):
            side = a[0]
            E, W = getattr(s, "E" + side), getattr(s, "W" + side)
            dv = (W - E) / (np.linalg.norm(W - E) + 1e-6)
            out.append(_box([E * 0.35 + W * 0.65, W + 12 * dv], 8))
        elif a in ("nfoot", "ffoot"):
            side = a[0]
            K, Av, Tt = getattr(s, "K" + side), getattr(s, "A" + side), getattr(s, "T" + side)
            out.append(_box([K * 0.4 + Av * 0.6, Av, Tt], 8))
        elif a == "weapon":
            wt = d.get("weapon")
            if wt is None:
                continue
            wa = p["wpn"] if p["wpn"] is not None else (70.0 if wt == "sword" else None)
            if wa is None:
                continue
            e = dvec(s.afn + wa)
            hc = s.Wn + 4 * s.hs * dvec(s.afn)
            ln, pad = (118, 13) if wt == "ruler" else (82, 6)
            n = 3
            for i in range(n):
                a0 = hc + e * (ln * i / n)
                a1 = hc + e * (ln * (i + 1) / n)
                out.append(_box([a0, a1], pad))
        elif a == "body":
            out.append(_box([s.P, s.C, s.Hc], 18 * s.hs))
    return out


def to_air_box(b):
    x0, y0, x1, y1 = b
    return (int(round(x0)), int(round(-y1)), int(round(x1)), int(round(-y0)))
