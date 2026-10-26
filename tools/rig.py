"""Skeleton, poses and costume assembly for the 2.5D fighters.

Angle conventions (degrees):
  lean   torso tilt, + = forward (top of body toward the opponent)
  rot    whole-body roll around the waist, + = forward roll
  head   head tilt relative to torso, + = look down/forward
  nsh/fsh   near/far shoulder: 0 = arm hanging, 90 = pointing forward, 180 = up (relative to torso)
  nel/fel   elbow bend, + = forearm swings further forward/up
  nhip/fhip near/far hip: 0 = leg straight down, + = leg forward (world relative)
  nknee/fknee knee bend, - = shin folds backward (natural)
  wpn    weapon angle relative to forearm (None = weapon stowed)
"""
import math

import numpy as np

from render3d import Canvas, Mat

DEFAULT_POSE = dict(rx=0.0, ry=None, lean=4.0, head=0.0, rot=0.0,
                    nsh=12.0, nel=22.0, fsh=-6.0, fel=28.0,
                    nhip=9.0, nknee=-6.0, nank=0.0, fhip=-9.0, fknee=-8.0, fank=0.0,
                    hair=0.0, cloth=0.0, wpn=None, nhand="fist", fhand="fist", sz=1.0,
                    twist=0.0, bob=0.0)

NUMERIC = [k for k, v in DEFAULT_POSE.items() if isinstance(v, float)]


def P(**kw):
    p = dict(DEFAULT_POSE)
    for k in kw:
        if k not in p:
            raise KeyError(k)
    p.update(kw)
    return p


def lerp_pose(a, b, t):
    out = {}
    for k in a:
        va, vb = a[k], b[k]
        if k == "ry":
            if va is None or vb is None:
                out[k] = None if t < 0.5 else vb
                if va is not None and vb is None:
                    out[k] = va if t < 0.5 else None
                continue
            out[k] = va + (vb - va) * t
        elif k == "wpn":
            if va is None or vb is None:
                out[k] = va if t < 0.5 else vb
            else:
                out[k] = va + (vb - va) * t
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            out[k] = va + (vb - va) * t
        else:
            out[k] = va if t < 0.5 else vb
    return out


def ease(t, kind="io"):
    if kind == "lin":
        return t
    if kind == "in":
        return t * t
    if kind == "out":
        return 1 - (1 - t) * (1 - t)
    return t * t * (3 - 2 * t)


def dvec(a):
    """unit vector pointing 'down' rotated CCW by a degrees."""
    r = math.radians(a)
    return np.array([math.sin(r), -math.cos(r)])


def uvec(a):
    """unit vector pointing 'up' rotated CW by a degrees (i.e. lean forward)."""
    r = math.radians(a)
    return np.array([math.sin(r), math.cos(r)])


def ang_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


# ---------------------------------------------------------------------------
# skeleton


class Skel:
    pass


def skeleton(p, d):
    """Forward kinematics -> Skel with 2D points (np arrays)."""
    hs = d.get("height", 1.0) * p["sz"]
    s = Skel()
    s.hs = hs
    lean, rot = p["lean"], p["rot"]
    ta = lean + rot
    T = uvec(ta)
    F = np.array([T[1], -T[0]])  # forward perpendicular
    s.T, s.F, s.ta = T, F, ta
    Pv = np.array([p["rx"], 0.0])
    s.P = Pv
    s.C = Pv + 58 * hs * T
    s.Nb = s.C + 2 * hs * T
    ha = ta + p["head"]
    s.ha = ha
    s.HU = uvec(ha)
    s.HF = np.array([s.HU[1], -s.HU[0]])
    s.Hc = s.Nb + 6 * hs * T + 14 * hs * s.HU
    S = s.C - 6 * hs * T
    s.S = S
    s.Sn = S + 3 * hs * F
    s.Sf = S - 5 * hs * F
    # arms (relative to torso)
    an = p["nsh"] - ta
    s.En = s.Sn + 31 * hs * dvec(an)
    s.afn = an + p["nel"]
    s.Wn = s.En + 29 * hs * dvec(s.afn)
    af = p["fsh"] - ta
    s.Ef = s.Sf + 31 * hs * dvec(af)
    s.aff = af + p["fel"]
    s.Wf = s.Ef + 29 * hs * dvec(s.aff)
    # legs (world relative, affected by roll)
    Hp = Pv - 2 * hs * T
    s.Hp = Hp
    for side in "nf":
        h = p[side + "hip"] - rot
        k = h + p[side + "knee"]
        K = Hp + 48 * hs * dvec(h)
        A = K + 46 * hs * dvec(k)
        Tt = A + 15 * hs * dvec(k + 90 + p[side + "ank"])
        setattr(s, "K" + side, K)
        setattr(s, "A" + side, A)
        setattr(s, "T" + side, Tt)
        setattr(s, "h" + side, h)
        setattr(s, "k" + side, k)
    return s


def ground_offset(p, d):
    """y shift so the lowest body point touches y=0 (ghosts hover)."""
    q = dict(p)
    q["ry"] = 0.0
    s = skeleton(q, d)
    if d.get("lower") == "ghost":
        if abs(p["rot"]) < 30:
            return 24.0 + 101 * s.hs
    hs = s.hs
    lows = [s.An[1] - 5, s.Tn[1] - 4, s.Af[1] - 5, s.Tf[1] - 4, s.P[1] - 14 * hs, s.C[1] - 16 * hs,
            s.Hc[1] - 16 * hs, s.Kn[1] - 8, s.Kf[1] - 8, s.Wn[1] - 6, s.Wf[1] - 6]
    if d.get("lower") == "ghost":
        lows = lows[4:7] + lows[9:]
    return -min(lows)


def resolve(p, d):
    p = dict(p)
    if p["ry"] is None:
        p["ry"] = ground_offset(p, d)
    p["ry"] = p["ry"] + p["bob"]
    p["bob"] = 0.0
    return p


# ---------------------------------------------------------------------------
# costume assembly


def v3(xy, z):
    return (float(xy[0]), float(xy[1]), float(z))


def build(cv: Canvas, p, d):
    """Draw character design `d` in pose `p` onto canvas `cv`."""
    p = resolve(p, d)
    s = skeleton(p, d)
    off = np.array([0.0, p["ry"]])
    for name in ("P", "C", "Nb", "Hc", "S", "Sn", "Sf", "En", "Wn", "Ef", "Wf", "Hp", "Kn", "An", "Tn", "Kf", "Af", "Tf"):
        setattr(s, name, getattr(s, name) + off)
    hs = s.hs
    bw = d.get("width", 1.0)
    M = d["mats"]
    T, F = s.T, s.F
    far = 0.86

    # ---------------- legs / lower body ----------------
    lower = d.get("lower", "robe")
    for side, z, k in (("n", 8, 1.0), ("f", -8, far)):
        K, A, Tt = getattr(s, "K" + side), getattr(s, "A" + side), getattr(s, "T" + side)
        if lower != "ghost":
            pants = M["pants"].darker(k) if k < 1 else M["pants"]
            shoe = M["shoe"].darker(k) if k < 1 else M["shoe"]
            cv.capsule(v3(s.Hp, z), v3(K, z), 8.6 * hs * bw, 7.0 * hs * bw, pants)
            cv.capsule(v3(K, z), v3(A, z), 7.0 * hs * bw, 5.0 * hs * bw, pants,
                       bands=d.get("shin_bands"))
            cv.capsule(v3(A, z), v3(Tt, z), 5.2 * hs, 4.2 * hs, shoe)

    # cloth panels
    sway = p["cloth"]
    if lower in ("dress", "robe"):
        long_ = lower == "dress"
        hem_r = d.get("hem_r", 19.0 if long_ else 16.5)
        hems = []
        for side, z, k in (("n", 10, 1.0), ("f", -10, far)):
            h, kk = getattr(s, "h" + side), getattr(s, "k" + side)
            robe = M["robe"].darker(k) if k < 1 else M["robe"]
            ha_ = h * 0.78 + sway
            Kp = s.Hp + 47 * hs * dvec(ha_)
            if long_:
                hem = Kp + 42 * hs * dvec(ha_ * 0.85 + (kk - h) * 0.3 + sway * 0.5)
                cv.capsule(v3(s.Hp, z), v3(Kp, z * 1.15), 14.5 * hs * bw, 15.5 * hs * bw, robe)
                cv.capsule(v3(Kp, z * 1.15), v3(hem, z * 1.25), 15.5 * hs * bw, hem_r * hs * bw, robe,
                           bands=[(0.9, 1.0, M["trim"].color)], open_end=True)
            else:
                hem = s.Hp + 60 * hs * dvec(ha_)
                cv.capsule(v3(s.Hp, z), v3(hem, z * 1.2), 14.0 * hs * bw, hem_r * hs * bw, robe,
                           bands=[(0.88, 1.0, M["trim"].color)], open_end=True)
            hems.append(hem)
        mid = (hems[0] + hems[1]) / 2
        if long_:
            mid = s.P + (mid - s.P) * 0.92
        else:
            mid = s.P + (mid - s.P) * 0.95
        cv.capsule(v3(s.P, 3), v3(mid, 6), 13.0 * hs * bw, (hem_r - 3) * hs * bw, M["robe2"], open_end=True)
        # back tail of robe
        back = s.P + 58 * hs * dvec(-14 - sway * 1.5 - p["rot"])
        cv.capsule(v3(s.P - 4 * F, -6), v3(back, -9), 13.0 * hs * bw, (hem_r - 1) * hs * bw,
                   M["robe"].darker(0.8), bands=[(0.9, 1.0, M["trim"].color * 0.8)], open_end=True)
    elif lower == "ghost":
        robe = M["robe"]
        m1 = s.P + 50 * hs * dvec(4 + sway - p["rot"])
        m2 = m1 + 40 * hs * dvec(-14 + sway * 1.6 - p["rot"])
        m3 = m2 + 26 * hs * dvec(-40 + sway * 2.2 - p["rot"])
        cv.capsule(v3(s.P, 0), v3(m1, 2), 16.5 * hs * bw, 17.5 * hs * bw, robe)
        cv.capsule(v3(m1, -2), v3(m2, -3), 15.0 * hs * bw, 9.0 * hs * bw, M["robe"].darker(0.92))
        cv.capsule(v3(m2, -4), v3(m3, -5), 9.0 * hs * bw, 1.5 * hs, M["robe"].darker(0.85))
        cv.capsule(v3(s.P, 6), v3(m1 + 6 * F, 8), 11.0 * hs * bw, 12.0 * hs * bw, M["robe2"], open_end=True)

    # ---------------- torso ----------------
    ta = s.ta
    robe = M["robe"]
    cv.ellipsoid(v3(s.P + 3 * hs * T, 0), 15.5 * hs * bw, 12 * hs, 13 * hs * bw, -ta, robe)
    cv.ellipsoid(v3(s.P + 21 * hs * T, 0), 13.5 * hs * bw, 16 * hs, 12.5 * hs * bw, -ta, robe)
    cv.ellipsoid(v3(s.P + 40 * hs * T + 1.0 * F, 0), 17.5 * hs * bw, 20 * hs, 15.5 * hs * bw, -ta, robe)
    if d.get("female"):
        cv.ellipsoid(v3(s.P + 42 * hs * T + 7.5 * hs * F, 5), 8.0 * hs, 7.5 * hs, 9.5 * hs, -ta, robe)
    # belt / sash
    cv.ellipsoid(v3(s.P + 17 * hs * T, 0), 14.6 * hs * bw, 3.6 * hs, 13.3 * hs * bw, -ta, M["belt"])
    if d.get("sash_tail", True):
        st = s.P + 17 * hs * T + 6 * hs * F
        cv.capsule(v3(st, 13), v3(st + 22 * hs * dvec(8 + sway - p["rot"]), 15), 2.6 * hs, 1.8 * hs, M["belt"])
    # collar (V neck trim)
    cv.capsule(v3(s.Nb - 1 * hs * T - 2 * F, 6), v3(s.P + 30 * hs * T + 11 * hs * F, 12.5), 2.6 * hs, 2.6 * hs, M["trim"])
    cv.capsule(v3(s.Nb - 1 * hs * T + 5 * F, 9), v3(s.P + 30 * hs * T + 11 * hs * F, 12.5), 2.2 * hs, 2.2 * hs, M["trim"])
    # shoulder pads/mantle
    if d.get("mantle"):
        cv.ellipsoid(v3(s.C - 4 * hs * T, -1), 19 * hs * bw, 9 * hs, 16 * hs * bw, -ta, M[d["mantle"]])
    # neck
    cv.capsule(v3(s.Nb - 4 * hs * T, 0), v3(s.Nb + 7 * hs * T, 1), 5.2 * hs, 5.0 * hs, M["skin"])

    # ---------------- arms ----------------
    for side, z, k in (("n", 14, 1.0), ("f", -14, far)):
        E, W = getattr(s, "E" + side), getattr(s, "W" + side)
        af = s.afn if side == "n" else s.aff
        sl = M["robe"].darker(k) if k < 1 else M["robe"]
        skin = M["skin"].darker(k) if k < 1 else M["skin"]
        cv.capsule(v3(getattr(s, "S" + side), z * 0.8), v3(E, z), 7.4 * hs * bw, 5.8 * hs * bw, sl)
        dirv = dvec(af)
        if d.get("sleeves", "wide") == "wide":
            cv.capsule(v3(E, z), v3(W - 1.0 * dirv, z + 1), 6.4 * hs * bw, 10.5 * hs * bw, sl,
                       bands=[(0.84, 1.0, M["trim"].color * (k if k < 1 else 1.0))], open_end=True)
            cv.capsule(v3(W - 6 * dirv, z), v3(W, z), 4.0 * hs, 3.8 * hs, skin)
        else:
            cv.capsule(v3(E, z), v3(W, z), 5.6 * hs * bw, 4.6 * hs * bw, sl,
                       bands=[(0.78, 1.0, M["trim"].color * (k if k < 1 else 1.0))])
        hand = p[side + "hand"]
        if hand == "open":
            c = W + 6 * hs * dirv
            cv.ellipsoid(v3(c, z + 1), 7.2 * hs, 4.0 * hs, 4.8 * hs, ang_of(dirv), skin)
            cv.capsule(v3(c + 0.5 * dirv + np.array([dirv[1], -dirv[0]]) * 2, z + 2),
                       v3(c + np.array([-dirv[1], dirv[0]]) * 5 - dirv * 2, z + 2), 1.9 * hs, 1.6 * hs, skin)
        elif hand == "claw":
            c = W + 5 * hs * dirv
            cv.ellipsoid(v3(c, z + 1), 6.5 * hs, 4.6 * hs, 5.0 * hs, ang_of(dirv), skin)
            for j in (-1, 0, 1):
                tip = c + 7 * dirv + np.array([-dirv[1], dirv[0]]) * j * 3
                cv.capsule(v3(c + 3 * dirv, z + 1), v3(tip, z + 1.5), 1.7, 1.3, skin)
        else:
            cv.sphere(v3(W + 4 * hs * dirv, z + 1), 5.6 * hs, skin)

    # ---------------- weapon ----------------
    wtype = d.get("weapon")
    if wtype == "ruler":
        if p["wpn"] is None:
            ang = 112 - ta
            c = s.C - 16 * hs * T - 4 * F
            cv.slab(v3(c, -22), ang, 64, 12, 5, M["weapon"], bands=d.get("weapon_bands"))
            cv.capsule(v3(s.C - 10 * hs * T + 9 * F, 13), v3(s.P + 14 * hs * T - 11 * F, 12), 1.8, 1.8, M["belt"])
        else:
            e = dvec(s.afn + p["wpn"])
            hc = s.Wn + 4 * hs * dvec(s.afn)
            c = hc + e * 52
            cv.slab(v3(c, 18), ang_of(e), 64, 12, 5, M["weapon"], bands=d.get("weapon_bands"))
    elif wtype == "sword":
        wa = p["wpn"] if p["wpn"] is not None else 70.0
        e = dvec(s.afn + wa)
        hc = s.Wn + 4 * hs * dvec(s.afn)
        cv.capsule(v3(hc - e * 7, 20), v3(hc + e * 5, 20), 2.2, 2.2, M["belt"])
        cv.slab(v3(hc + e * 7, 20.5), ang_of(e) + 90, 7, 2.2, 2, M["gold"], bevel=1.2)
        cv.slab(v3(hc + e * 44, 20), ang_of(e), 37, 2.6, 1.6, M["weapon"], bevel=1.4)

    # ---------------- head ----------------
    HU, HF, Hc, ha = s.HU, s.HF, s.Hc, s.ha
    cv.ellipsoid(v3(Hc, 0), 12.5 * hs, 15 * hs, 12.5 * hs, -ha, M["skin"])
    cv.ellipsoid(v3(Hc + 5 * hs * HF - 6.5 * hs * HU, 0), 7.5 * hs, 7.5 * hs, 9.6 * hs, -ha, M["skin"])
    # eyes
    eye = M["eye"]
    cv.ellipsoid(v3(Hc + 6.2 * hs * HF + 1.2 * hs * HU, 9.6 * hs), 1.8 * hs, 3.0 * hs, 1.2, -ha, eye)
    cv.ellipsoid(v3(Hc + 11.0 * hs * HF + 1.2 * hs * HU, 5.0 * hs), 1.4 * hs, 2.8 * hs, 1.2, -ha, eye)
    brow = M["brow"]
    cv.capsule(v3(Hc + 4 * hs * HF + 5.4 * hs * HU, 10.2 * hs), v3(Hc + 9 * hs * HF + 5.6 * hs * HU, 9.0 * hs), 0.9, 0.8, brow)
    hair = M["hair"]
    style = d.get("hair", "long")
    # cap
    cv.ellipsoid(v3(Hc - 2.8 * hs * HF + 2.6 * hs * HU, -0.5), 14.2 * hs, 16.2 * hs, 13.0 * hs, -ha, hair)
    # bangs
    for j, (zz, dx_) in enumerate(((11, 0.0), (8, 2.5), (4, 4.0), (12.5, -2.5))):
        a = Hc + (4 + dx_) * hs * HF + 13 * hs * HU
        b = Hc + (10 + dx_ * 0.6) * hs * HF + (4.5 - j * 0.6) * hs * HU
        cv.capsule(v3(a, zz), v3(b, zz + 0.5), 3.6 * hs, 1.2 * hs, hair)
    # side lock framing the face
    cv.capsule(v3(Hc + 1.5 * hs * HF + 7 * hs * HU, 11.5 * hs), v3(Hc + 3 * hs * HF - (12 if style != "spiky" else 6) * hs * HU, 12.0 * hs),
               3.4 * hs, 1.4 * hs, hair)
    sway_h = p["hair"]
    if style in ("long", "pony", "bun", "old"):
        length = d.get("hair_len", 5)
        for zz, wid, k in ((-7, 1.05, 0.88), (0, 1.15, 0.94), (5, 0.9, 1.0)):
            pt = Hc - 7 * hs * HF + 5 * hs * HU
            a = -4 - p["rot"] * 0.3 - sway_h
            for i in range(length):
                a2 = a - 1.5 - sway_h * 0.4 * (i + 1) / length
                nxt = pt + 15 * hs * dvec(a2 - (p["lean"] * 0.4 if i == 0 else 0))
                r0 = (10 - i * 1.3) * hs * wid
                r1 = (10 - (i + 1) * 1.3) * hs * wid
                cv.capsule(v3(pt, zz), v3(nxt, zz - 1), max(r0, 3.5), max(r1, 2.5), hair.darker(k) if k < 1 else hair)
                pt = nxt
                a = a2
        if style == "pony":
            rb = M.get("ribbon", M["trim"])
            q = Hc - 11 * hs * HF + 6 * hs * HU
            cv.ellipsoid(v3(q, 2), 5, 3.5, 4, -ha + 30, rb)
            cv.capsule(v3(q, 3), v3(q + 16 * dvec(-30 - sway_h), 4), 2.5, 1.2, rb)
            cv.capsule(v3(q, 3), v3(q + 14 * dvec(-5 - sway_h), 4), 2.5, 1.2, rb)
    if style == "spiky":
        for j, (u, v, ang, ln, zz) in enumerate(((-9, 9, 135, 13, -3), (-11, 3, 165, 12, 2), (-10, -4, 200, 10, -1),
                                                   (-3, 14, 110, 10, 4), (-8, 12, 150, 12, 6))):
            a = Hc + u * hs * HF + v * hs * HU
            dv = np.array([math.cos(math.radians(ang - ha)), math.sin(math.radians(ang - ha))])
            cv.capsule(v3(a, zz), v3(a + dv * ln * hs, zz), 4.6 * hs, 0.9 * hs, hair)
        # nape
        a = Hc - 8 * hs * HF - 2 * hs * HU
        cv.capsule(v3(a, -2), v3(a + 18 * hs * dvec(-20 - sway_h - p["rot"] * 0.3), -3), 7 * hs, 2 * hs, hair)
    if style in ("bun", "old"):
        q = Hc - 6 * hs * HF + 14 * hs * HU
        cv.sphere(v3(q, -1), 7.5 * hs, hair)
        pin = M.get("pin", M["gold"])
        cv.slab(v3(q, 6), 25 - ha, 13, 1.4, 1.5, pin, bevel=0.7)
        cv.sphere(v3(q + np.array([math.cos(math.radians(25 - ha)), math.sin(math.radians(25 - ha))]) * 13, 7.5), 2.4, pin)
    if style == "old":
        # long beard + moustache
        chin = Hc + 6 * hs * HF - 12 * hs * HU
        pt = chin
        for i in range(4):
            nxt = pt + 11 * hs * dvec(8 - i * 3 - p["rot"] - sway_h * 0.5)
            cv.capsule(v3(pt, 10), v3(nxt, 10.5), (6.5 - i * 1.2) * hs, (5.3 - i * 1.2) * hs, hair)
            pt = nxt
        m0 = Hc + 9 * hs * HF - 6 * hs * HU
        cv.capsule(v3(m0, 12), v3(m0 + np.array([-4, -9]) * hs, 12), 2.2, 1.0, hair)
        cv.capsule(v3(m0, 12), v3(m0 + np.array([5, -8]) * hs, 12.5), 2.2, 1.0, hair)
    if d.get("crown"):
        g = M["gold"]
        base = Hc - 1 * hs * HF + 14 * hs * HU
        cv.ellipsoid(v3(base, 2), 11 * hs, 2.6 * hs, 11 * hs, -ha, g)
        for j, dd in enumerate((-8, -3.5, 1, 5.5)):
            a = base + dd * hs * HF + 1.5 * HU
            tip = a + (10 if j in (1, 2) else 7) * hs * HU
            cv.capsule(v3(a, 4 + j), v3(tip, 4 + j), 2.2, 0.6, g)
        cv.sphere(v3(base + 1 * HF + 3 * HU, 12), 2.4, M["jewel"])
    if d.get("hairflower"):
        q = Hc - 3 * hs * HF + 11 * hs * HU
        for j in range(5):
            aa = j * 72
            pp = q + 3.2 * np.array([math.cos(math.radians(aa)), math.sin(math.radians(aa))])
            cv.sphere(v3(pp, 11), 2.6, M[d["hairflower"]])
        cv.sphere(v3(q, 12.5), 1.6, M["gold"])
    return s


def default_mats(c):
    """Build Mat objects from a dict of colours."""
    m = {}
    m["skin"] = Mat(c["skin"], outline=0.45, rim=0.12, shadow_tint=(0.95, 0.82, 0.86))
    m["hair"] = Mat(c["hair"], spec=c.get("hair_spec", 0.22), outline=0.45, rim=0.25)
    m["robe"] = Mat(c["robe"], outline=0.35)
    m["robe2"] = Mat(c.get("robe2", c["robe"]), outline=0.35)
    m["trim"] = Mat(c["trim"], spec=0.1, outline=0.4)
    m["belt"] = Mat(c["belt"], outline=0.4)
    m["pants"] = Mat(c["pants"], outline=0.35)
    m["shoe"] = Mat(c["shoe"], outline=0.4)
    m["eye"] = Mat(c["eye"], outline=1.0, rim=0, bands=(-2, -3), shadow_tint=(1, 1, 1))
    m["brow"] = Mat(c.get("brow", c["hair"]), outline=1.0, rim=0, bands=(-2, -3), shadow_tint=(1, 1, 1))
    m["gold"] = Mat(c.get("gold", (0.95, 0.76, 0.28)), spec=0.4, outline=0.4)
    m["weapon"] = Mat(c.get("weapon", (0.18, 0.17, 0.2)), spec=0.35, outline=0.5)
    for k, v in c.items():
        if k not in m and isinstance(v, tuple):
            m[k] = Mat(v, spec=0.25, outline=0.4)
    return m
