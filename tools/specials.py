"""Special-move and super animations for each fighter.

Frames may carry ev="name": the CNS generator looks these up to time projectiles,
hitboxes and effects to the matching AnimElem."""
from anims import F, tween, mod, jump_pose
from rig import lerp_pose


def palm_push(sty, two=False, low=False, hold=14):
    s = sty.stance
    base = sty.crouch if low else s
    wind = mod(base, nsh=10, nel=120, fsh=40, fel=110, lean=base["lean"] - 6, nhand="open", fhand="open",
               hair=-2)
    if two:
        push = mod(base, nsh=88, nel=0, fsh=82, fel=6, lean=base["lean"] + 14, nhand="open", fhand="open",
                   nhip=32, nknee=-44, fhip=-26, fknee=-8, cloth=-8, hair=-8)
    else:
        push = mod(base, nsh=90, nel=0, fsh=-20, fel=50, lean=base["lean"] + 14, nhand="open",
                   nhip=32, nknee=-44, fhip=-26, fknee=-8, cloth=-8, hair=-8)
    if sty.sword:
        push = mod(push, wpn=170)
    fr = tween(base, wind, 2, 3)
    fr += [F(wind, 5)]
    fr += [F(lerp_pose(wind, push, 0.6), 2), F(push, 4, ev="spawn"), F(push, hold)]
    fr += tween(push, s, 3, 5)
    return dict(frames=fr)


def rising(sty, weapon=False, spin=False):
    s = sty.stance
    c = mod(sty.crouch, nsh=20, nel=100)
    up = mod(s, nsh=170, nel=6, fsh=-30, fel=40, lean=-8, head=-20, nhip=70, nknee=-100, fhip=-10, fknee=-20,
             hair=-16, cloth=14, nhand="open" if not weapon else "fist")
    if weapon:
        up = mod(up, wpn=10)
    top = mod(jump_pose(sty, "top"), nsh=150, nel=20)
    if weapon:
        top = mod(top, wpn=30)
    fr = [F(c, 3), F(lerp_pose(c, up, 0.5), 2, ["weapon" if weapon else "nhand", "body"], ev="rise")]
    if spin:
        for i in range(4):
            fr.append(F(mod(up, rot=0, twist=0, nsh=170 - i * 10, lean=-8 + (i % 2) * 6), 3,
                        ["weapon" if weapon else "nhand", "body"]))
    else:
        fr.append(F(up, 6, ["weapon" if weapon else "nhand", "body"]))
    fr += [F(top, 6), F(jump_pose(sty, "down"), -1, ev="fall")]
    return dict(frames=fr, loop=len(fr) - 1)


def lunge(sty, claw=True):
    s = sty.stance
    coil = mod(s, lean=s["lean"] - 6, nsh=10, nel=110, nhip=40, nknee=-90, fhip=-10, fknee=-60, hair=-4)
    dash = mod(s, lean=44, nsh=88, nel=0, fsh=-40, fel=20, nhip=60, nknee=-60, fhip=-50, fknee=-20, cloth=-20,
               hair=28, nhand="claw" if claw else "open")
    if sty.sword:
        dash = mod(dash, wpn=4, nhand="fist")
    fr = [F(coil, 4), F(coil, 6), F(dash, 3, ["nhand" if not sty.sword else "weapon", "body"], ev="go"),
          F(dash, 3, ["nhand" if not sty.sword else "weapon", "body"]),
          F(dash, 3, ["nhand" if not sty.sword else "weapon", "body"]),
          F(dash, 3, ["nhand" if not sty.sword else "weapon", "body"])]
    fr += tween(dash, s, 3, 5)
    return dict(frames=fr)


def octane(sty):
    """Ba Ji Beng: dash then a palm that detonates eight times."""
    s = sty.stance
    coil = mod(s, lean=s["lean"] - 4, nsh=-10, nel=100, nhand="open", nhip=40, nknee=-80, fhip=-14, fknee=-40)
    dash = mod(s, lean=36, nsh=70, nel=30, nhand="open", nhip=60, nknee=-50, fhip=-50, fknee=-10, cloth=-18,
               hair=20)
    palm = mod(s, lean=24, nsh=92, nel=0, nhand="open", fsh=-30, fel=60, nhip=40, nknee=-50, fhip=-30, fknee=-6,
               cloth=-10, hair=-6)
    fr = [F(coil, 5), F(dash, 3, ev="go"), F(dash, 3), F(palm, 4, ["nhand"], ev="palm")]
    for i in range(5):
        fr.append(F(mod(palm, rx=(i % 2) * 2, lean=24 + (i % 2) * 3), 5, ["nhand"]))
    fr[-1]["ev"] = "palm_end"
    fr += tween(palm, s, 3, 6)
    return dict(frames=fr)


def overhead_slam(sty):
    """Flame Splitting Tsunami: ruler raised overhead, slammed to the ground."""
    s = sty.stance
    up = mod(s, nsh=175, nel=10, fsh=165, fel=10, wpn=175, lean=-10, head=-14, nhip=10, nknee=-10, fhip=-10,
             fknee=-6, hair=-6)
    slam = mod(s, nsh=70, nel=10, fsh=60, fel=10, wpn=0, lean=36, head=14, nhip=50, nknee=-60, fhip=-34,
               fknee=-6, cloth=-10, hair=12)
    fr = tween(s, up, 3, 4)
    fr += [F(up, 8, ev="charge"), F(lerp_pose(up, slam, 0.5), 2, ["weapon"]), F(slam, 3, ["weapon"], ev="spawn"),
           F(slam, 18)]
    fr += tween(slam, s, 3, 6)
    return dict(frames=fr)


def powerup(sty):
    s = sty.stance
    a = mod(s, nsh=50, nel=110, fsh=50, fel=110, lean=10, head=12, nhip=26, nknee=-40, fhip=-24, fknee=-30)
    b = mod(s, nsh=135, nel=20, fsh=125, fel=20, lean=-12, head=-24, nhip=30, nknee=-30, fhip=-30, fknee=-20,
            nhand="open", fhand="open", hair=-24, cloth=16)
    fr = tween(s, a, 2, 4) + [F(a, 14, ev="charge"), F(b, 4, ev="burst"), F(b, 30)]
    fr += tween(b, s, 3, 5)
    return dict(frames=fr)


def summon_up(sty, two=True):
    s = sty.stance
    up = mod(s, nsh=175, nel=0, fsh=170 if two else -20, fel=0 if two else 40, lean=-6, head=-26,
             nhand="open", fhand="open", hair=-10, cloth=10)
    if sty.sword:
        up = mod(up, wpn=0)
    point = mod(s, nsh=95, nel=0, fsh=90 if two else -20, fel=0 if two else 40, lean=16, head=0,
                nhand="open", fhand="open", nhip=30, nknee=-40, fhip=-24, fknee=-8, cloth=-10, hair=-10)
    if sty.sword:
        point = mod(point, wpn=0)
    fr = tween(s, up, 3, 4) + [F(up, 24, ev="charge"), F(lerp_pose(up, point, 0.5), 3),
                               F(point, 6, ev="spawn"), F(point, 40)]
    fr += tween(point, s, 3, 6)
    return dict(frames=fr)


def ground_touch(sty):
    s = sty.stance
    kneel = mod(sty.crouch, nsh=95, nel=10, lean=38, head=10, nhand="open", nhip=70, nknee=-120, fhip=-30,
                fknee=-90)
    fr = tween(s, kneel, 3, 4) + [F(kneel, 4, ev="spawn"), F(kneel, 16)]
    fr += tween(kneel, s, 3, 5)
    return dict(frames=fr)


def flip_kick(sty):
    s = sty.stance
    fr = [F(mod(sty.crouch, lean=20), 3)]
    tuck = mod(jump_pose(sty, "top"), nhip=80, nknee=-130, fhip=70, fknee=-130)
    for i in range(6):
        ang = -60 * (i + 1)
        k = mod(tuck, rot=ang)
        if i in (2, 3):
            k = mod(k, nhip=150, nknee=-4, fhip=60)
            fr.append(F(k, 3, ["nfoot", "body"], ev="kick" if i == 2 else None))
        else:
            fr.append(F(k, 3, ["body"] if i > 0 else None))
    fr += [F(jump_pose(sty, "down"), -1, ev="fall")]
    return dict(frames=fr, loop=len(fr) - 1)


def combo_palms(sty, n=5, weapon=False):
    s = sty.stance
    fr = []
    for i in range(n):
        near = i % 2 == 0
        if weapon:
            hi = mod(s, nsh=140 if near else 40, nel=10, wpn=30 if near else 10, lean=14 + 4 * (i % 2),
                     nhip=30, nknee=-40, fhip=-20, fknee=-10, hair=-6 + 4 * (i % 2))
            lo = mod(s, nsh=50 if near else 130, nel=10, wpn=10 if near else 40, lean=20,
                     nhip=34, nknee=-46, fhip=-24, fknee=-8, cloth=-8)
            fr += [F(hi, 2), F(lo, 4, ["weapon"], ev="hit%d" % i)]
        else:
            if near:
                p = mod(s, nsh=92, nel=0, nhand="open", fsh=10, fel=110, lean=20 + i * 2, nhip=34, nknee=-44,
                        fhip=-26, fknee=-8, cloth=-8)
                atk = ["nhand"]
            else:
                p = mod(s, fsh=92, fel=0, fhand="open", nsh=10, nel=110, lean=22, nhip=34, nknee=-44, fhip=-26,
                        fknee=-8, cloth=-8)
                atk = ["fhand"]
            fr += [F(lerp_pose(s, p, 0.4), 2), F(p, 5, atk, ev="hit%d" % i)]
    fin = mod(s, nsh=90, nel=0, fsh=85, fel=4, nhand="open", fhand="open", lean=26, nhip=40, nknee=-50,
              fhip=-30, fknee=-6, cloth=-12, hair=-10)
    if weapon:
        fin = mod(fin, wpn=0, fsh=-30, fel=40)
    fr += [F(fin, 6, ["nhand"] if not weapon else ["weapon"], ev="final"), F(fin, 24)]
    fr += tween(fin, s, 3, 5)
    return dict(frames=fr)


def lotus(sty):
    """Buddha's Angry Lotus: compress flames between both hands, then hurl."""
    s = sty.stance
    form = mod(s, nsh=70, nel=60, fsh=72, fel=60, nhand="open", fhand="open", lean=4, head=6, nhip=24,
               nknee=-30, fhip=-22, fknee=-20)
    lift = mod(s, nsh=160, nel=30, fsh=155, fel=30, nhand="open", fhand="open", lean=-10, head=-20,
               hair=-12, cloth=10)
    hurl = mod(s, nsh=95, nel=0, fsh=-10, fel=50, nhand="open", lean=28, nhip=42, nknee=-50, fhip=-30, fknee=-6,
               cloth=-14, hair=-14)
    fr = tween(s, form, 3, 4) + [F(form, 30, ev="form"), F(lerp_pose(form, lift, 0.5), 4), F(lift, 30, ev="lift"),
                                 F(lerp_pose(lift, hurl, 0.5), 3), F(hurl, 6, ev="spawn"), F(hurl, 50)]
    fr += tween(hurl, s, 3, 6)
    return dict(frames=fr)


def pill(sty):
    s = sty.stance
    cup = mod(s, nsh=60, nel=80, fsh=55, fel=85, nhand="open", fhand="open", head=14, lean=6)
    up = mod(cup, nsh=80, nel=110, head=-6)
    fr = tween(s, cup, 2, 4) + [F(cup, 24, ev="refine"), F(up, 8, ev="eat"), F(up, 20)]
    fr += tween(up, s, 2, 5)
    return dict(frames=fr)


def soul_point(sty):
    s = sty.stance
    temple = mod(s, nsh=110, nel=150, nhand="open", head=6, lean=4)
    push = mod(s, nsh=92, nel=0, nhand="open", lean=12, nhip=20, nknee=-30, fhip=-20, fknee=-10, cloth=-6,
               hair=-6)
    fr = tween(s, temple, 2, 4) + [F(temple, 14, ev="charge"), F(push, 4, ev="spawn"), F(push, 22)]
    fr += tween(push, s, 3, 5)
    return dict(frames=fr)


def vanish(sty):
    s = sty.stance
    a = mod(s, lean=20, nsh=-30, fsh=-40, cloth=-14, hair=20)
    return dict(frames=[F(a, 4), F(a, 16, ev="out", hurt=False)] + [F(s, 6, ev="in")])


def make_specials(key, sty):
    """Returns {anim_id: anim} for this fighter's specials and supers."""
    A = {}
    if key == "xiaoyan":
        A[1000] = octane(sty)
        A[1100] = overhead_slam(sty)
        A[1200] = rising(sty, weapon=True)
        A[3000] = powerup(sty)
        A[3100] = lotus(sty)
    elif key == "yaolao":
        A[1000] = palm_push(sty)
        A[1100] = soul_point(sty)
        A[1200] = pill(sty)
        A[1300] = vanish(sty)
        A[3000] = palm_push(sty, two=True, hold=60)
        A[3100] = summon_up(sty, two=False)
    elif key == "xuner":
        A[1000] = palm_push(sty)
        A[1100] = rising(sty, spin=True)
        A[1200] = flip_kick(sty)
        A[3000] = combo_palms(sty, 5)
        A[3100] = summon_up(sty)
    elif key == "medusa":
        A[1000] = palm_push(sty)
        A[1100] = lunge(sty)
        A[1200] = palm_push(sty, hold=10)
        A[3000] = palm_push(sty, two=True, hold=50)
        A[3100] = summon_up(sty, two=False)
    elif key == "yunyun":
        A[1000] = combo_palms(sty, 1, weapon=True)
        A[1100] = rising(sty, weapon=True, spin=True)
        A[1200] = vanish(sty)
        A[3000] = combo_palms(sty, 6, weapon=True)
        A[3100] = summon_up(sty, two=False)
    elif key == "fairydoctor":
        A[1000] = palm_push(sty)
        A[1100] = lunge(sty, claw=False)
        A[1200] = ground_touch(sty)
        A[3000] = powerup(sty)
        A[3100] = summon_up(sty)
    return A
