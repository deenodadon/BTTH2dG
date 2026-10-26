"""Animation library: keyframed poses for every MUGEN action of every fighter.

Each animation is a list of frames: dict(pose, t=ticks, atk=[...], hurt=bool).
`atk` lists what carries the hitbox on that frame: "nhand", "fhand", "nfoot", "ffoot",
"weapon", "body" or a ("box", x0, y0, x1, y1) in world units (y up).
Animations may set "loop" (frame index to loop from) and "trans" (e.g. "add").
"""
import math

from rig import P, lerp_pose, ease


def F(pose, t, atk=None, hurt=True, **kw):
    f = dict(pose=pose, t=t, atk=atk, hurt=hurt)
    f.update(kw)
    return f


def tween(a, b, n, t, kind="io", atk=None, include_last=True, **kw):
    """n frames moving from pose a to pose b."""
    out = []
    for i in range(n):
        k = (i + 1) / n if include_last else i / n
        out.append(F(lerp_pose(a, b, ease(k, kind)), t, atk, **kw))
    return out


def mod(p, **kw):
    q = dict(p)
    q.update(kw)
    return q


# ---------------------------------------------------------------------------
# styles


class Style:
    def __init__(self, key, d):
        self.key = key
        self.d = d
        self.female = d.get("female", False)
        self.ghost = d.get("lower") == "ghost"
        self.sword = d.get("weapon") == "sword"
        self.ruler = d.get("weapon") == "ruler"
        if self.ghost:
            self.stance = P(lean=3, head=-2, nsh=42, nel=48, nhand="open", fsh=-35, fel=70,
                            nhip=6, nknee=-10, fhip=-6, fknee=-10, cloth=-4)
        elif self.sword:
            self.stance = P(lean=6, head=-4, nsh=42, nel=38, wpn=58, fsh=20, fel=105, fhand="open",
                            nhip=18, nknee=-18, fhip=-16, fknee=-12, hair=4)
        elif self.female:
            self.stance = P(lean=5, head=-3, nsh=34, nel=72, nhand="open", fsh=48, fel=58, fhand="open",
                            nhip=15, nknee=-16, fhip=-13, fknee=-10, hair=3)
        else:
            self.stance = P(lean=9, head=-5, nsh=38, nel=78, fsh=22, fel=88,
                            nhip=21, nknee=-26, fhip=-19, fknee=-20)
        self.crouch = mod(self.stance, lean=self.stance["lean"] + 14, nhip=70, nknee=-125, fhip=40,
                          fknee=-120, head=-8, nsh=self.stance["nsh"] + 10, fsh=self.stance["fsh"] + 10)
        if self.ghost:
            self.crouch = mod(self.stance, lean=16, head=-6, bob=-46, cloth=6)


def stance(sty, **kw):
    return mod(sty.stance, **kw)


# ---------------------------------------------------------------------------
# basic movement


def anim_idle(sty):
    s = sty.stance
    fr = []
    for i in range(8):
        ph = math.sin(i / 8 * 2 * math.pi)
        if sty.ghost:
            q = mod(s, bob=4 * ph, cloth=-4 + 3 * math.cos(i / 8 * 2 * math.pi), hair=2 * ph)
        else:
            q = mod(s, nknee=s["nknee"] - 4 - 4 * ph, fknee=s["fknee"] - 4 - 4 * ph,
                    nhip=s["nhip"] + 2 + 2 * ph, fhip=s["fhip"] + 1 + 1 * ph,
                    nsh=s["nsh"] + 2 * ph, fsh=s["fsh"] + 2 * ph, hair=s["hair"] + 2 * ph,
                    cloth=1.5 * ph)
        fr.append(F(q, 7))
    return dict(frames=fr, loop=0)


def anim_walk(sty, back=False):
    s = sty.stance
    fr = []
    n = 8
    for i in range(n):
        ph = i / n * 2 * math.pi
        if back:
            ph = -ph
        if sty.ghost:
            q = mod(s, bob=3 * math.sin(2 * ph), cloth=(-9 if not back else 6), lean=s["lean"] + (4 if not back else -4))
        else:
            sw = math.sin(ph)
            q = mod(s, nhip=6 + 22 * sw, fhip=-6 - 22 * sw,
                    nknee=-10 - 26 * max(0.0, math.cos(ph)), fknee=-10 - 26 * max(0.0, -math.cos(ph)),
                    nsh=s["nsh"] - 6 * sw, fsh=s["fsh"] + 6 * sw,
                    cloth=(-5 if not back else 5) + 3 * sw, hair=s["hair"] + 3,
                    bob=2.5 * abs(math.cos(ph)))
        fr.append(F(q, 5))
    return dict(frames=fr, loop=0)


def anim_run(sty):
    s = sty.stance
    fr = []
    n = 6
    for i in range(n):
        ph = i / n * 2 * math.pi
        if sty.ghost or sty.female:
            # gliding dash with trailing sleeves
            q = mod(s, lean=s["lean"] + 22, nsh=-30, nel=20, fsh=-40, fel=15, nhip=40 + 8 * math.sin(ph),
                    nknee=-60, fhip=-40 + 8 * math.sin(ph), fknee=-30, cloth=-18, hair=24,
                    bob=4 * math.sin(2 * ph))
            if sty.ghost:
                q = mod(q, bob=4 * math.sin(2 * ph), cloth=-14)
            if sty.sword:
                q = mod(q, wpn=100)
        else:
            sw = math.sin(ph)
            q = mod(s, lean=26, nhip=10 + 45 * sw, fhip=10 - 45 * sw,
                    nknee=-30 - 60 * max(0.0, math.cos(ph)), fknee=-30 - 60 * max(0.0, -math.cos(ph)),
                    nsh=20 - 50 * sw, nel=90, fsh=20 + 50 * sw, fel=90, cloth=-14, hair=16,
                    bob=5 * abs(math.cos(ph)))
        fr.append(F(q, 4))
    return dict(frames=fr, loop=0)


def anim_hopback(sty):
    s = sty.stance
    a = mod(s, lean=-10, nhip=40, nknee=-70, fhip=10, fknee=-60, cloth=10, hair=-6)
    b = mod(s, lean=-4, nhip=20, nknee=-40, fhip=-5, fknee=-30, cloth=6)
    return dict(frames=[F(a, 4), F(b, 6), F(s, 30)])


def anim_crouch_trans(sty, down=True):
    a, b = sty.stance, sty.crouch
    if not down:
        a, b = b, a
    mid = lerp_pose(a, b, 0.5)
    return dict(frames=[F(mid, 3), F(b, 3)])


def anim_crouch(sty):
    c = sty.crouch
    fr = []
    for i in range(4):
        ph = math.sin(i / 4 * 2 * math.pi)
        fr.append(F(mod(c, nsh=c["nsh"] + 2 * ph, hair=c["hair"] + ph, bob=c["bob"] + ph * 0.8), 9))
    return dict(frames=fr, loop=0)


def jump_pose(sty, phase):
    s = sty.stance
    if sty.ghost:
        return mod(s, cloth=8 if phase == "up" else -6, bob=0, hair=-8 if phase == "up" else 6)
    if phase == "up":
        return mod(s, lean=2, nhip=60, nknee=-110, fhip=10, fknee=-60, nsh=60, fsh=40, cloth=10,
                   hair=-10)
    if phase == "top":
        return mod(s, lean=10, nhip=80, nknee=-130, fhip=50, fknee=-120, nsh=50, fsh=60, cloth=4, hair=-2)
    return mod(s, lean=4, nhip=30, nknee=-40, fhip=-8, fknee=-30, nsh=70, fsh=60, cloth=-8, hair=10)


def anim_jumpstart(sty):
    c = mod(sty.stance, nhip=40, nknee=-80, fhip=10, fknee=-70, lean=14)
    if sty.ghost:
        c = mod(sty.stance, bob=-8, cloth=6)
    return dict(frames=[F(c, 3)])


def anim_jump(sty, kind):
    up, top, down = jump_pose(sty, "up"), jump_pose(sty, "top"), jump_pose(sty, "down")
    if kind == "fwd" and not sty.ghost:
        fr = [F(up, 4)]
        for i in range(1, 7):
            fr.append(F(mod(top, rot=i * 60), 4))
        fr.append(F(down, 4))
        return dict(frames=fr, loop=len(fr) - 1)
    if kind == "back" and not sty.ghost:
        fr = [F(up, 4)]
        for i in range(1, 7):
            fr.append(F(mod(top, rot=-i * 60), 4))
        fr.append(F(down, 4))
        return dict(frames=fr, loop=len(fr) - 1)
    return dict(frames=[F(up, 6), F(lerp_pose(up, top, 0.6), 6), F(top, 8), F(down, 6)], loop=3)


def anim_land(sty):
    c = mod(sty.stance, nhip=45, nknee=-90, fhip=15, fknee=-80, lean=16, cloth=6)
    if sty.ghost:
        c = mod(sty.stance, bob=-6, cloth=6)
    return dict(frames=[F(c, 3), F(lerp_pose(c, sty.stance, 0.5), 3)])


def anim_turn(sty, crouch=False):
    b = sty.crouch if crouch else sty.stance
    return dict(frames=[F(mod(b, lean=b["lean"] - 4, nsh=b["nsh"] - 15, fsh=b["fsh"] + 10), 3),
                        F(b, 3)])


# ---------------------------------------------------------------------------
# guard / hit


def guard_pose(sty, crouch=False, air=False):
    b = sty.crouch if crouch else sty.stance
    if air:
        b = jump_pose(sty, "top")
    g = mod(b, nsh=110, nel=110, fsh=95, fel=120, head=6, lean=b["lean"] - 2, nhand="fist", fhand="fist")
    if sty.sword:
        g = mod(g, wpn=90)
    return g


def anim_guard(sty, crouch=False, air=False):
    return dict(frames=[F(guard_pose(sty, crouch, air), -1)])


def anim_guardstart(sty, crouch=False):
    b = sty.crouch if crouch else sty.stance
    return dict(frames=[F(lerp_pose(b, guard_pose(sty, crouch), 0.5), 2), F(guard_pose(sty, crouch), 2)])


def anim_guardhit(sty, crouch=False, air=False):
    g = guard_pose(sty, crouch, air)
    h = mod(g, lean=g["lean"] - 8, rx=-4, head=10)
    return dict(frames=[F(h, 3), F(g, -1)])


def hit_pose(sty, level, kind="high"):
    s = sty.stance
    k = {0: 0.6, 1: 1.0, 2: 1.4}[level]
    if kind == "high":
        return mod(s, lean=s["lean"] - 22 * k, head=-25 * k, rx=-6 * k, nsh=-20, nel=40, fsh=-30, fel=30,
                   nhand="open", fhand="open", hair=10, cloth=6)
    if kind == "low":
        return mod(s, lean=s["lean"] + 30 * k, head=20 * k, rx=-4 * k, nsh=-15, nel=30, fsh=-10, fel=40,
                   nhand="open", fhand="open", nhip=30, nknee=-40, hair=12, cloth=8)
    if kind == "crouch":
        c = sty.crouch
        return mod(c, lean=c["lean"] - 20 * k, head=-20 * k, nsh=-10, fsh=-20, nhand="open", fhand="open", hair=10)


def anim_hit(sty, level, kind):
    h = hit_pose(sty, level, kind)
    base = sty.crouch if kind == "crouch" else sty.stance
    ticks = [3, 4, 6][level]
    fr = [F(h, ticks), F(lerp_pose(h, base, 0.35), ticks + 2)]
    return dict(frames=fr)


def anim_hit_recover(sty, kind):
    base = sty.crouch if kind == "crouch" else sty.stance
    h = hit_pose(sty, 1, kind)
    return dict(frames=[F(lerp_pose(h, base, 0.6), 3), F(base, 3)])


def air_hit_pose(sty, t=0.0):
    """t: 0 = just hit (arched), 1 = flat falling."""
    s = sty.stance
    a = mod(s, lean=-30, head=-30, nsh=-60, nel=20, fsh=-80, fel=30, nhip=40, nknee=-50, fhip=20, fknee=-70,
            nhand="open", fhand="open", hair=20, cloth=14)
    b = mod(a, rot=-60, lean=-20)
    return lerp_pose(a, b, t)


def lying_pose(sty, ph=0.0):
    s = sty.stance
    return mod(s, rot=-88, lean=-4, head=-10 + 4 * ph, nsh=-110 + 10 * ph, nel=20, fsh=-140, fel=10, nhip=8,
               nknee=-12, fhip=22, fknee=-34, nhand="open", fhand="open", hair=-80, cloth=0)


def anim_air_hit(sty):
    return dict(frames=[F(air_hit_pose(sty, 0.0), 4), F(air_hit_pose(sty, 0.2), -1)])


def anim_air_trans(sty):
    return dict(frames=[F(air_hit_pose(sty, 0.4), 4), F(air_hit_pose(sty, 0.7), 4)])


def anim_air_up(sty):
    return dict(frames=[F(mod(air_hit_pose(sty, 0.1), rot=10), 4), F(air_hit_pose(sty, 0.0), -1)])


def anim_fall(sty):
    fr = [F(air_hit_pose(sty, 0.8), 4), F(mod(air_hit_pose(sty, 1.0), nsh=-40), 4),
          F(mod(air_hit_pose(sty, 1.0), nsh=-70, nhip=55), 4)]
    return dict(frames=fr, loop=1)


def anim_trip(sty):
    a = mod(sty.stance, rot=-40, lean=-10, nhip=70, nknee=-20, fhip=40, fknee=-30, nsh=-60, fsh=-80,
            nhand="open", fhand="open", hair=30)
    return dict(frames=[F(a, 4), F(mod(a, rot=-60), -1)])


def anim_bounce(sty):
    return dict(frames=[F(mod(lying_pose(sty), rot=-80, nhip=40, fhip=60, nknee=-40), 3),
                        F(mod(lying_pose(sty), rot=-70, nhip=50, fhip=70), 3),
                        F(mod(lying_pose(sty), rot=-75, nhip=40, fhip=50), -1)])


def anim_lying(sty, dead=False):
    if dead:
        return dict(frames=[F(lying_pose(sty, 0.0), 20, hurt=False), F(lying_pose(sty, 1.0), -1, hurt=False)])
    return dict(frames=[F(lying_pose(sty, 0.0), -1, hurt=False)])


def anim_getup(sty):
    s = sty.stance
    l0 = lying_pose(sty)
    sit = mod(s, rot=-30, lean=10, nhip=80, nknee=-60, fhip=90, fknee=-120, nsh=-40, fsh=-50, nel=10, fel=10,
              hair=-10, nhand="open", fhand="open")
    kneel = mod(s, lean=20, nhip=80, nknee=-130, fhip=-20, fknee=-110, nsh=10, fsh=-20)
    fr = [F(lerp_pose(l0, sit, 0.4), 6, hurt=False), F(sit, 6, hurt=False),
          F(kneel, 6, hurt=False), F(lerp_pose(kneel, s, 0.5), 5, hurt=False), F(s, 5, hurt=False)]
    return dict(frames=fr)


def anim_lie_hit(sty):
    l0 = lying_pose(sty)
    return dict(frames=[F(mod(l0, rot=-75, head=10, nhip=30, fhip=40), 4), F(l0, -1)])


def anim_recover(sty, near_ground=False):
    fr = []
    for i in range(6):
        fr.append(F(mod(jump_pose(sty, "top"), rot=-i * 60 if not near_ground else -i * 30), 3))
    fr.append(F(jump_pose(sty, "down"), -1))
    return dict(frames=fr)


def anim_dizzy(sty):
    s = sty.stance
    fr = []
    for i in range(6):
        ph = math.sin(i / 6 * 2 * math.pi)
        fr.append(F(mod(s, lean=20 + 6 * ph, head=25, rx=4 * ph, nsh=-5, fsh=-10, nel=10, fel=10,
                        nhand="open", fhand="open", hair=4 * ph), 6))
    return dict(frames=fr, loop=0)


def anim_lose(sty):
    s = sty.stance
    a = mod(s, lean=30, head=30, nsh=-5, nel=10, fsh=-8, fel=8, nhand="open", fhand="open",
            nhip=10, nknee=-30, fhip=-6, fknee=-20)
    return dict(frames=[F(lerp_pose(s, a, 0.5), 8), F(a, -1)])


# ---------------------------------------------------------------------------
# normals (generic, style-tweaked)


def _strike(sty, wind, hit, rec_t=(5, 5), act_t=3, atk=("nhand",), wind_t=(3,), pre=None):
    s = pre if pre is not None else sty.stance
    fr = []
    for i, t in enumerate(wind_t):
        k = (i + 1) / len(wind_t)
        fr.append(F(lerp_pose(s, wind, ease(k)), t))
    fr.append(F(hit, act_t, list(atk)))
    fr.append(F(lerp_pose(hit, s, 0.35), rec_t[0]))
    fr.append(F(lerp_pose(hit, s, 0.75), rec_t[1]))
    return dict(frames=fr)


def anim_lp(sty):
    s = sty.stance
    if sty.sword:
        wind = mod(s, nsh=60, nel=20, wpn=40)
        hit = mod(s, nsh=88, nel=4, wpn=8, lean=14, nhip=26, nknee=-32)
        return _strike(sty, wind, hit, atk=("weapon",), wind_t=(2,))
    wind = mod(s, nsh=25, nel=110, nhand="fist")
    hit = mod(s, nsh=86, nel=4, lean=s["lean"] + 6, nhand="open" if sty.female or sty.ghost else "fist")
    return _strike(sty, wind, hit, wind_t=(2,))


def anim_hp(sty):
    s = sty.stance
    if sty.ruler:
        wind = mod(s, nsh=150, nel=20, wpn=170, lean=-6, fsh=40, fel=90)
        mid = mod(s, nsh=120, nel=10, wpn=60, lean=10)
        hit = mod(s, nsh=70, nel=0, wpn=20, lean=26, nhip=34, nknee=-46, fhip=-26, fknee=-6, hair=-8)
        fr = [F(lerp_pose(s, wind, 0.5), 4), F(wind, 5), F(mid, 2, ["weapon"]), F(hit, 4, ["weapon"]),
              F(lerp_pose(hit, s, 0.3), 7), F(lerp_pose(hit, s, 0.7), 7)]
        return dict(frames=fr)
    if sty.sword:
        wind = mod(s, nsh=140, nel=20, wpn=40, lean=-4, twist=0)
        mid = mod(s, nsh=100, nel=10, wpn=20, lean=8)
        hit = mod(s, nsh=50, nel=0, wpn=10, lean=22, nhip=30, nknee=-40)
        fr = [F(wind, 4), F(mid, 2, ["weapon"]), F(hit, 4, ["weapon"]), F(lerp_pose(hit, s, 0.3), 6),
              F(lerp_pose(hit, s, 0.7), 6)]
        return dict(frames=fr)
    wind = mod(s, nsh=10, nel=120, lean=s["lean"] - 6, fsh=60, fel=70)
    hit = mod(s, nsh=90, nel=0, lean=s["lean"] + 18, rx=6, nhip=36, nknee=-48, fhip=-26, fknee=-8,
              nhand="open" if (sty.female or sty.ghost) else "fist", fsh=-20, fel=40, hair=-6, cloth=-6)
    return _strike(sty, wind, hit, rec_t=(7, 8), act_t=4, wind_t=(3, 3))


def anim_lk(sty):
    s = sty.stance
    wind = mod(s, nhip=60, nknee=-100, lean=s["lean"] - 6)
    hit = mod(s, nhip=72, nknee=-6, nank=-10, lean=s["lean"] - 14, fhip=-10, fknee=-6, cloth=8)
    return _strike(sty, wind, hit, atk=("nfoot",), wind_t=(2,))


def anim_hk(sty):
    s = sty.stance
    wind = mod(s, nhip=80, nknee=-120, lean=-10, fhip=-10, fknee=-8, cloth=6)
    hit = mod(s, nhip=110, nknee=-2, nank=-20, lean=-26, fhip=-14, fknee=-4, nsh=-10, fsh=60, cloth=14,
              hair=-12)
    return _strike(sty, wind, hit, rec_t=(7, 8), act_t=4, atk=("nfoot",), wind_t=(3, 3))


def anim_clp(sty):
    c = sty.crouch
    hit = mod(c, nsh=84, nel=4, nhand="open" if sty.female or sty.ghost else "fist")
    if sty.sword:
        hit = mod(hit, wpn=6)
        return _strike(sty, mod(c, nsh=60, nel=30), hit, atk=("weapon",), wind_t=(2,), pre=c)
    return _strike(sty, mod(c, nsh=30, nel=100), hit, wind_t=(2,), pre=c)


def anim_chp(sty):
    c = sty.crouch
    wind = mod(c, nsh=0, nel=100)
    hit = mod(sty.stance, nsh=168, nel=8, lean=-6, nhip=30, nknee=-50, fhip=-10, fknee=-30, head=-20,
              hair=-10, cloth=8)
    if sty.ruler:
        hit = mod(hit, wpn=10)
        return _strike(sty, mod(wind, wpn=60), hit, rec_t=(6, 8), act_t=5, atk=("weapon", "nhand"),
                       wind_t=(3,), pre=c)
    if sty.sword:
        hit = mod(hit, wpn=10)
        return _strike(sty, mod(wind, wpn=60), hit, rec_t=(6, 8), act_t=5, atk=("weapon",), wind_t=(3,), pre=c)
    return _strike(sty, wind, hit, rec_t=(6, 8), act_t=5, atk=("nhand",), wind_t=(3,), pre=c)


def anim_clk(sty):
    c = sty.crouch
    hit = mod(c, nhip=88, nknee=-4, nank=-30, lean=c["lean"] - 16)
    return _strike(sty, mod(c, nhip=60, nknee=-80), hit, atk=("nfoot",), wind_t=(2,), pre=c)


def anim_chk(sty):
    c = sty.crouch
    hit = mod(c, nhip=92, nknee=-2, nank=-20, lean=c["lean"] + 4, fhip=50, fknee=-140, nsh=-20, fsh=-40,
              rx=4, cloth=10)
    return _strike(sty, mod(c, nhip=40, nknee=-100, lean=c["lean"] + 10), hit, rec_t=(8, 8), act_t=4,
                   atk=("nfoot",), wind_t=(3, 3), pre=c)


def anim_jlp(sty):
    j = jump_pose(sty, "top")
    hit = mod(j, nsh=60, nel=0, nhand="open" if sty.female or sty.ghost else "fist", lean=16)
    if sty.sword:
        hit = mod(hit, wpn=40)
        return dict(frames=[F(mod(j, nsh=80, nel=60), 2), F(hit, 6, ["weapon"]), F(j, 6)])
    return dict(frames=[F(mod(j, nsh=20, nel=100), 2), F(hit, 6, ["nhand"]), F(j, 6)])


def anim_jhp(sty):
    j = jump_pose(sty, "top")
    if sty.ruler or sty.sword:
        wind = mod(j, nsh=170, nel=10, wpn=40, lean=-10)
        hit = mod(j, nsh=60, nel=0, wpn=20, lean=30)
        return dict(frames=[F(wind, 4), F(lerp_pose(wind, hit, 0.5), 2, ["weapon"]), F(hit, 5, ["weapon"]),
                            F(lerp_pose(hit, j, 0.5), 8)])
    hit = mod(j, nsh=40, nel=0, fsh=50, fel=0, nhand="open", fhand="open", lean=30, head=10)
    return dict(frames=[F(mod(j, nsh=120, nel=60, fsh=130), 4), F(hit, 6, ["nhand", "fhand"]),
                        F(lerp_pose(hit, j, 0.5), 8)])


def anim_jlk(sty):
    j = jump_pose(sty, "top")
    hit = mod(j, nhip=60, nknee=-10, fhip=60, fknee=-130, lean=-6, nank=-20)
    return dict(frames=[F(lerp_pose(j, hit, 0.5), 2), F(hit, 8, ["nfoot"]), F(j, 6)])


def anim_jhk(sty):
    j = jump_pose(sty, "top")
    hit = mod(j, nhip=40, nknee=-4, fhip=80, fknee=-130, lean=-18, nank=-30, rot=20)
    return dict(frames=[F(mod(j, rot=10), 3), F(hit, 6, ["nfoot"]), F(lerp_pose(hit, j, 0.5), 8)])


def anim_throw_try(sty):
    s = sty.stance
    hit = mod(s, nsh=80, nel=10, fsh=75, fel=15, nhand="claw", fhand="claw", lean=s["lean"] + 10)
    return dict(frames=[F(lerp_pose(s, hit, 0.5), 2), F(hit, 4, ["nhand"]), F(lerp_pose(hit, s, 0.5), 10)])


def anim_throw(sty):
    s = sty.stance
    grab = mod(s, nsh=80, nel=10, fsh=75, fel=15, nhand="claw", fhand="claw", lean=s["lean"] + 10)
    lift = mod(s, nsh=150, nel=20, fsh=140, fel=20, lean=-14, head=-15)
    hurl = mod(s, nsh=60, nel=0, fsh=40, fel=0, lean=30, nhip=40, nknee=-50, nhand="open", fhand="open")
    return dict(frames=[F(grab, 6), F(lift, 8), F(hurl, 6, ["nhand"]), F(lerp_pose(hurl, s, 0.5), 10),
                        F(s, 6)])


def anim_win(sty):
    s = sty.stance
    if sty.ruler:
        a = mod(s, nsh=120, nel=20, wpn=110, lean=0, head=-8, fsh=-10, fel=10, nhip=10, nknee=-6, fhip=-10, fknee=-6)
        b = mod(a, nsh=95, wpn=150)
    elif sty.ghost:
        a = mod(s, nsh=30, nel=110, fsh=-35, fel=70, head=10, nhand="open", cloth=-6)
        b = mod(a, nsh=40, nel=120, head=4, bob=3)
    elif sty.sword:
        a = mod(s, nsh=10, nel=20, wpn=10, lean=0, fsh=-10, fel=100, head=-5, nhip=6, nknee=-4, fhip=-6, fknee=-4)
        b = mod(a, hair=8)
    else:
        a = mod(s, nsh=-10, nel=40, fsh=-15, fel=40, lean=0, head=-6, nhip=6, nknee=-4, fhip=-6, fknee=-4,
                nhand="open", fhand="open")
        b = mod(a, hair=8, cloth=3)
    fr = tween(s, a, 4, 4)
    fr += [F(a, 20), F(b, 20), F(a, 20)]
    return dict(frames=fr, loop=len(fr) - 3)


def anim_intro(sty):
    s = sty.stance
    if sty.ghost:
        a = mod(s, bob=-60, cloth=10)
        return dict(frames=tween(a, s, 8, 5, kind="out") + [F(s, 20)])
    bow = mod(s, lean=30, head=20, nsh=60, nel=100, fsh=60, fel=100, nhand="fist", fhand="open",
              nhip=4, nknee=-4, fhip=-4, fknee=-4)
    fr = [F(mod(s, lean=0, nhip=4, nknee=-4, fhip=-4, fknee=-4), 20)]
    fr += tween(fr[0]["pose"], bow, 3, 5)
    fr += [F(bow, 20)]
    fr += tween(bow, s, 4, 5)
    return dict(frames=fr)


def anim_taunt(sty):
    s = sty.stance
    a = mod(s, nsh=100, nel=60, nhand="open", lean=0, head=-10, fsh=-10, fel=20)
    b = mod(a, nel=90)
    return dict(frames=[F(a, 8), F(b, 8), F(a, 8), F(b, 8), F(s, 8)])
