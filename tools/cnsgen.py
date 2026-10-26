"""Generates MUGEN/Ikemen character files (.def .cns .cmd .air) from the animation tables."""
import random


class St:
    """A [Statedef] block with its state controllers."""

    def __init__(self, no, comment="", **hdr):
        self.no = no
        self.comment = comment
        self.hdr = hdr
        self.ctrls = []

    def add(self, typ, trig, p=None, all=None, label=""):
        self.ctrls.append((typ, trig, p or {}, all, label))
        return self

    def text(self):
        out = []
        if self.comment:
            out.append("; " + self.comment)
        out.append("[Statedef %s]" % self.no)
        for k, v in self.hdr.items():
            out.append("%s = %s" % (k.replace("_", "."), v))
        out.append("")
        for i, (typ, trig, p, al, label) in enumerate(self.ctrls):
            out.append("[State %s, %s]" % (self.no, label or typ))
            out.append("type = %s" % typ)
            if al:
                for a in (al if isinstance(al, list) else [al]):
                    out.append("triggerall = %s" % a)
            trigs = trig if isinstance(trig, list) else [trig]
            for j, t in enumerate(trigs):
                if isinstance(t, (list, tuple)):  # AND-group for one trigger number
                    for tt in t:
                        out.append("trigger%d = %s" % (j + 1, tt))
                else:
                    out.append("trigger%d = %s" % (j + 1, t))
            for k, v in p.items():
                out.append("%s = %s" % (k, v))
            out.append("")
        return "\n".join(out)


# --------------------------------------------------------------------------------------
# HitDef presets

STR = {
    "L": dict(pausetime="8, 8", slide=8, hittime=11, vel="-5", air="-3,-5", anim="Light", snd="S2,0",
              spark="0", gpause="6, 6"),
    "M": dict(pausetime="11, 11", slide=11, hittime=14, vel="-6.5", air="-3.5,-6", anim="Medium", snd="S2,1",
              spark="1", gpause="8, 8"),
    "H": dict(pausetime="13, 13", slide=14, hittime=18, vel="-8", air="-4,-7", anim="Hard", snd="S2,2",
              spark="2", gpause="10, 10"),
}


def hitdef(strength, dmg, attr="S, NA", guard="MA", gtype="High", fall=False, sparkxy="-10, -140",
           chip=None, spark=None, extra=None, hitflag="MAF", priority="4, Hit"):
    s = STR[strength]
    p = {
        "attr": attr,
        "damage": "%d, %d" % (dmg, chip if chip is not None else (dmg // 8 if "S" in attr.split(",")[1] or "H" in attr.split(",")[1] else 0)),
        "animtype": s["anim"],
        "guardflag": guard,
        "hitflag": hitflag,
        "priority": priority,
        "pausetime": s["pausetime"],
        "guard.pausetime": s["gpause"],
        "sparkno": spark if spark is not None else s["spark"],
        "guard.sparkno": "40",
        "sparkxy": sparkxy,
        "hitsound": s["snd"],
        "guardsound": "S2,3",
        "ground.type": gtype,
        "ground.slidetime": s["slide"],
        "ground.hittime": s["hittime"],
        "guard.slidetime": s["slide"],
        "guard.hittime": s["hittime"],
        "guard.ctrltime": s["hittime"],
        "ground.velocity": s["vel"],
        "guard.velocity": "-6",
        "air.velocity": s["air"],
        "airguard.velocity": "-4,-4",
        "air.hittime": s["hittime"],
        "getpower": "%d, %d" % (dmg, dmg // 2),
        "givepower": "%d, %d" % (dmg // 2, dmg // 4),
    }
    if fall:
        p.update({"fall": 1, "fall.recover": 1, "air.fall": 1, "fall.recovertime": 30})
    if extra:
        p.update(extra)
    return p


def fx_explod(anim, pos="0, 0", postype="p1", eid=None, extra=None):
    p = {"anim": anim, "ID": eid if eid is not None else anim, "pos": pos, "postype": postype,
         "facing": 1, "removetime": -2, "sprpriority": 4, "ownpal": 1, "ignorehitpause": 1,
         "supermovetime": 9999, "pausemovetime": 9999}
    if extra:
        p.update(extra)
    return p


def snd(group, idx, channel=None, extra=None):
    p = {"value": "%d, %d" % (group, idx)}
    if channel is not None:
        p["channel"] = channel
    if extra:
        p.update(extra)
    return p


# --------------------------------------------------------------------------------------
# context


class Ctx:
    def __init__(self, key, name, anims, fx):
        self.key = key
        self.name = name
        self.anims = anims  # body animation table {id: anim}
        self.fx = fx        # effect table
        self.states = []
        self.cmd_entries = []   # (comment, St-ctrl tuple)
        self.ai_entries = []

    def E(self, aid, ev):
        """AnimElem number of event `ev` in body animation aid."""
        fr = self.anims[aid]["frames"]
        for i, f in enumerate(fr):
            if f.get("ev") == ev:
                return i + 1
        raise KeyError("anim %d has no event %s" % (aid, ev))

    def nfr(self, aid):
        return len(self.anims[aid]["frames"])

    def first_atk(self, aid):
        for i, f in enumerate(self.anims[aid]["frames"]):
            if f.get("atk"):
                return i + 1
        return 1

    def total_ticks(self, aid):
        return sum(max(f["t"], 0) for f in self.anims[aid]["frames"])

    def elem_tick(self, aid, elem):
        """tick (from state start) at which element `elem` begins."""
        return sum(max(f["t"], 0) for f in self.anims[aid]["frames"][:elem - 1])

    def state(self, *a, **k):
        st = St(*a, **k)
        self.states.append(st)
        return st


# --------------------------------------------------------------------------------------
# generic states


def normal_state(c, no, aid, kind, strength, dmg, gtype="High", fall=False, air=False, attr=None,
                 voice=None, swing=None, low=False, overhead=False, launcher=False, extra=None):
    stype = "A" if air else ("C" if kind == "C" else "S")
    phys = "A" if air else stype
    st = c.state(no, "", type=stype, movetype="A", physics=phys, juggle=4 if strength != "L" else 2,
                 poweradd=10 if strength == "L" else 25, ctrl=0, anim=aid, sprpriority=2,
                 **({} if air else {"velset": "0,0"}))
    a1 = c.first_atk(aid)
    st.add("PlaySnd", "AnimElem = %d" % max(1, a1 - 1), snd(1, 1 if strength == "H" else 0))
    if voice is not None:
        st.add("PlaySnd", ["Time = 1 && Random < %d" % voice], snd(0, 1 if strength == "H" else 0, 0))
    guard = "HA" if air else ("L" if low else ("H" if overhead else "MA"))
    if attr is None:
        attr = ("A" if air else ("C" if kind == "C" else "S")) + ", " + ("HA" if strength == "H" else "NA")
    p = hitdef(strength, dmg, attr=attr, guard=guard, gtype=gtype, fall=fall,
               sparkxy="-10, %d" % (-150 if not low else -50))
    if launcher:
        p.update({"air.velocity": "-2.5,-12", "ground.velocity": "-2.5,-12", "air.juggle": 4, "fall": 1,
                  "air.fall": 1, "ground.type": "High"})
        p["fall.recover"] = 1
    if gtype == "Trip":
        p.update({"ground.velocity": "-2,-5", "fall": 1, "fall.recover": 0})
    if extra:
        p.update(extra)
    st.add("HitDef", "AnimElem = %d" % a1, p)
    if air:
        st.add("CtrlSet", "AnimTime = 0", {"value": 1})
        st.add("ChangeAnim", "AnimTime = 0", {"value": 41, "elem": 3})
    else:
        st.add("ChangeState", "AnimTime = 0", {"value": 11 if kind == "C" else 0, "ctrl": 1})
    return st


def build_common(c, d):
    """Normals, throw, win, intro, taunt."""
    heavy_weapon = d.get("weapon") == "ruler"
    normal_state(c, 200, 200, "S", "L", 30, voice=350)
    normal_state(c, 210, 210, "S", "H", 70 if not heavy_weapon else 80, voice=700)
    normal_state(c, 230, 230, "S", "L", 35, voice=350)
    normal_state(c, 240, 240, "S", "H", 75, voice=700, fall=False)
    normal_state(c, 400, 400, "C", "L", 25)
    normal_state(c, 410, 410, "C", "H", 70, voice=700, launcher=True)
    normal_state(c, 430, 430, "C", "L", 30, low=True, gtype="Low")
    normal_state(c, 440, 440, "C", "H", 65, low=True, gtype="Trip", voice=700)
    normal_state(c, 600, 600, "A", "L", 35, air=True)
    normal_state(c, 610, 610, "A", "H", 70, air=True, voice=700)
    normal_state(c, 630, 630, "A", "L", 40, air=True)
    normal_state(c, 640, 640, "A", "H", 70, air=True, voice=700)

    # throw attempt
    st = c.state(800, "Throw attempt", type="S", movetype="A", physics="S", juggle=0, ctrl=0, anim=800,
                 velset="0,0", sprpriority=2)
    st.add("HitDef", "AnimElem = %d" % c.first_atk(800), {
        "attr": "S, NT", "hitflag": "M-", "priority": "1, Miss", "sparkno": -1, "guardflag": "",
        "p1sprpriority": 1, "p2sprpriority": 0, "p1facing": 1, "p2facing": 1,
        "p1stateno": 810, "damage": "0", "ground.velocity": 0, "ground.hittime": 40, "ground.slidetime": 0,
        "ground.type": "High", "air.velocity": "0,0", "fall": 0, "numhits": 0, "pausetime": "0, 0",
        "hitsound": -1})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    st = c.state(810, "Throw", type="S", movetype="A", physics="N", ctrl=0, anim=810, velset="0,0",
                 sprpriority=2, poweradd=60)
    hurl = c.first_atk(810)
    st.add("PlaySnd", "Time = 0", snd(0, 9, 0))
    st.add("TargetBind", "AnimElemNo(0) < 2", {"pos": "62, 0"})
    st.add("TargetBind", "AnimElemNo(0) = [2, %d]" % (hurl - 1), {"pos": "44, -70"})
    st.add("HitDef", "AnimElem = %d" % hurl, hitdef(
        "H", 90, attr="S, NT", guard="", fall=True, sparkxy="0,-100", spark="S6020", hitflag="MAFD",
        priority="7, Hit", extra={"ground.velocity": "-9,-8", "air.velocity": "-9,-8", "fall.recover": 0,
                                  "air.juggle": 0, "p2facing": 1}))
    st.add("Explod", "AnimElem = %d" % hurl, fx_explod(6020, "70, -100"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})

    # win
    st = c.state(180, "Win pose", type="S", ctrl=0, anim=180, velset="0,0")
    st.add("PlaySnd", "Time = 10", snd(0, 7, 0))
    st.add("AssertSpecial", "1", {"flag": "noautoturn"})
    # intro (overrides common 191)
    st = c.state(191, "Intro", type="S", ctrl=0, anim=190, velset="0,0")
    st.add("PlaySnd", "Time = 8", snd(0, 8, 0))
    st.add("Explod", "Time = 0", fx_explod(6010, "0, -100", extra={"scale": "1.6,1.6"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # taunt
    st = c.state(195, "Taunt", type="S", movetype="I", physics="S", ctrl=0, anim=195, velset="0,0")
    st.add("PlaySnd", "Time = 2", snd(0, 7, 0))
    st.add("PowerAdd", "Time = 20", {"value": 100})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})


def build_minus2(c, d, extra=None):
    st = St(-2, "Always-run logic")
    st.add("VarSet", "RoundState = 0", {"var(10)": 0}, all="!IsHelper")
    st.add("PlaySnd", [("!Alive", "var(10) = 0")], snd(0, 6, 0), all="!IsHelper", label="KO voice")
    st.add("VarSet", "!Alive", {"var(10)": 1}, all="!IsHelper")
    st.add("PlaySnd", [("StateNo = [5000, 5030]", "Time = 1", "Random < 450")],
           snd(0, 4, 0), all=["!IsHelper", "Alive"], label="hurt voice")
    st.add("PlaySnd", [("StateNo = 5050", "Time = 1", "Random < 600")],
           snd(0, 5, 0), all=["!IsHelper", "Alive"], label="hurt voice heavy")
    st.add("Explod", [("StateNo = 52", "Time = 0")], fx_explod(6000, "0, 0", extra={"sprpriority": -1}),
           all="!IsHelper", label="landing dust")
    st.add("PlaySnd", [("StateNo = 52", "Time = 0")], snd(1, 3), all="!IsHelper")
    st.add("PlaySnd", [("StateNo = 40", "Time = 0")], snd(1, 4), all="!IsHelper")
    st.add("PlaySnd", [("StateNo = 20", "AnimElemTime(1) = 0 || AnimElemTime(5) = 0")], snd(1, 2),
           all="!IsHelper")
    if extra:
        for e in extra:
            st.add(*e)
    return st


# --------------------------------------------------------------------------------------
# special-move builders


def proj_state(c, no, aid, cost=0, projanim=None, hitanim=None, vel=(9, 0), dmg=70, hits=1, misstime=0,
               offset=(70, -130), name="", sndid=(3, 0), strength="H", fall=False, pid=None,
               scale=None, removetime=-1, guard="MA", extra=None, attr="S, SP", voice=True, priority=2,
               fx_charge=None):
    st = c.state(no, name, type="S", movetype="A", physics="S", juggle=4, poweradd=40 if not cost else 0,
                 ctrl=0, anim=aid, velset="0,0", sprpriority=2)
    spawn = c.E(aid, "spawn")
    if voice:
        st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    if fx_charge:
        st.add("Explod", "Time = 2", fx_explod(fx_charge, "40, -120"))
    st.add("PlaySnd", "AnimElem = %d" % spawn, snd(*sndid))
    p = {"projid": pid or no, "projanim": projanim, "projhitanim": hitanim, "projremanim": hitanim,
         "projcancelanim": hitanim, "projremove": 1, "projremovetime": removetime,
         "velocity": "%s, %s" % vel, "offset": "%d, %d" % offset, "projpriority": priority,
         "projhits": hits, "projmisstime": misstime, "projsprpriority": 4, "projshadow": "0,0,0"}
    if scale:
        p["projscale"] = scale
    h = hitdef(strength, dmg, attr=attr, guard=guard, fall=fall, sparkxy="0, 0", spark="S6020")
    if extra:
        h.update(extra)
    p.update(h)
    st.add("Projectile", "AnimElem = %d" % spawn, p)
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    return st


def super_start(st, c, cost, flash_pos="0, -110"):
    st.add("PowerAdd", "Time = 0", {"value": -cost})
    st.add("SuperPause", "Time = 0", {"time": 40, "anim": -1, "sound": "S4,0", "pos": "0, -110",
                                       "darken": 1, "p2defmul": 1, "poweradd": 0, "unhittable": 1})
    st.add("Explod", "Time = 0", fx_explod(6010, flash_pos, extra={"scale": "1.8,1.8", "sprpriority": 5}))
    st.add("PlaySnd", "Time = 1", snd(0, 3, 0))
    st.add("AfterImage", "Time = 0", {"time": 40, "length": 10, "palbright": "30,30,30",
                                       "palcontrast": "120,120,220", "trans": "add", "timegap": 2,
                                       "framegap": 4})


def helper(c, hid, stateno, pos, postype="p1", extra=None, name="fx"):
    p = {"helpertype": "normal", "name": '"%s"' % name, "ID": hid, "stateno": stateno, "pos": pos,
         "postype": postype, "facing": 1, "keyctrl": 0, "ownpal": 1, "supermovetime": 0,
         "pausemovetime": 0}
    if extra:
        p.update(extra)
    return p


def helper_state(c, no, anim, life, hit=None, every=0, nhits=1, vel=None, first=0, name="",
                 bind=None, sndid=None, follow_p2=False, shake=None, extra_ctrls=None):
    """An attack helper: plays `anim`, deals hit (HitDef params) `nhits` times every `every` ticks."""
    st = c.state(no, name, type="A", movetype="A", physics="N", anim=anim, ctrl=0, sprpriority=4,
                 velset="%s, %s" % (vel if vel else (0, 0)))
    st.add("AssertSpecial", "1", {"flag": "noshadow"})
    st.add("PlayerPush", "1", {"value": 0})
    if sndid:
        st.add("PlaySnd", "Time = 0", snd(*sndid))
    if shake:
        st.add("EnvShake", "Time = %d" % first, {"time": shake, "freq": 60, "ampl": 6})
    if hit:
        if nhits > 1 and every:
            trig = [("Time >= %d" % first, "Time <= %d" % (first + every * (nhits - 1)),
                     "(Time - %d) %% %d = 0" % (first, every))]
        else:
            trig = "Time = %d" % first
        st.add("HitDef", trig, hit)
    if extra_ctrls:
        for e in extra_ctrls:
            st.add(*e)
    st.add("DestroySelf", "Time >= %d" % life)
    return st


# --------------------------------------------------------------------------------------
# per-character move sets


def moves_xiaoyan(c):
    # 1000 Octane Blast (Ba Ji Beng): dashing palm, eight hidden detonations
    a = 1000
    st = c.state(1000, "Octane Blast (Ba Ji Beng)", type="S", movetype="A", physics="S", juggle=4, ctrl=0,
                 anim=a, velset="0,0", sprpriority=2, poweradd=40)
    go, palm, pend = c.E(a, "go"), c.E(a, "palm"), c.E(a, "palm_end")
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("VelSet", "AnimElem = %d" % go, {"x": "ifelse(var(1), 12, 9)"})
    st.add("VelSet", "AnimElem = %d" % palm, {"x": 0})
    st.add("PlaySnd", "AnimElem = %d" % go, snd(1, 4))
    p = hitdef("M", 28, attr="S, SA", sparkxy="0, -130", spark="S6100",
               extra={"hitsound": "S3,0", "ground.hittime": 30, "ground.slidetime": 4, "ground.velocity": "-1",
                      "air.velocity": "-1,-2", "pausetime": "3,6", "guard.pausetime": "3,6"})
    st.add("HitDef", "AnimElem = %d" % palm, p)
    rearm = [("MoveHit", "AnimElemTime(%d) > 0" % palm, "AnimElemTime(%d) < 22" % palm,
              "AnimElemTime(%d) %% 3 = 0" % palm)]
    st.add("HitDef", rearm, p, label="hidden detonations")
    last = dict(p)
    last.update({"damage": "45, 4", "fall": 1, "fall.recover": 0, "ground.velocity": "-9,-5",
                 "air.velocity": "-9,-5", "hitsound": "S3,0"})
    st.add("HitDef", [("MoveHit", "AnimElemTime(%d) = 22" % palm)], last, label="final burst")
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 1100 Flame Splitting Tsunami: ruler slam -> travelling fire wave
    proj_state(c, 1100, 1100, projanim=6110, hitanim=6111, vel=(8, 0), dmg=80, hits=2, misstime=6,
               offset=(110, 0), name="Flame Splitting Tsunami", sndid=(3, 1), fall=True)
    st = c.states[-1]
    st.add("EnvShake", "AnimElem = %d" % c.E(1100, "spawn"), {"time": 12, "ampl": 5, "freq": 60})
    # 1200 rising flame ruler (anti-air)
    rising_state(c, 1200, 1200, dmg=90, fxanim=6120, sndid=(3, 2))
    # 3000 Skyfire Three Mysterious Change (power-up)
    st = c.state(3000, "Skyfire Three Mysterious Change", type="S", movetype="A", physics="S", ctrl=0,
                 anim=3000, velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    burst = c.E(3000, "burst")
    st.add("PlaySnd", "AnimElem = %d" % burst, snd(3, 3))
    st.add("VarSet", "AnimElem = %d" % burst, {"var(0)": 600})
    st.add("HitDef", "AnimElem = %d" % burst, hitdef("H", 60, attr="S, HA", fall=True, sparkxy="0,-100",
                                                      spark="S6020",
                                                      extra={"ground.velocity": "-10,-6", "air.velocity": "-10,-6"}))
    st.add("Explod", "AnimElem = %d" % burst, fx_explod(6111, "0, -100", extra={"scale": "1.6,1.6"}))
    st.add("EnvShake", "AnimElem = %d" % burst, {"time": 20, "ampl": 7, "freq": 60})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 3100 Buddha's Angry Lotus
    st = c.state(3100, "Buddha's Angry Lotus", type="S", movetype="A", physics="S", ctrl=0, anim=3100,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 3000)
    form, spawn = c.E(3100, "form"), c.E(3100, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % form, snd(3, 4))
    st.add("Explod", "AnimElem = %d" % form, fx_explod(6140, "52, -128", eid=6140,
                                                       extra={"removetime": 70, "bindtime": -1}))
    st.add("RemoveExplod", "AnimElem = %d" % spawn, {"ID": 6140})
    st.add("Helper", "AnimElem = %d" % spawn, helper(c, 7100, 7100, "70, -150", name="Angry Lotus"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # lotus flight
    st = c.state(7100, "Lotus projectile (helper)", type="A", movetype="A", physics="N", anim=6141, ctrl=0,
                 sprpriority=5, velset="7, 0")
    st.add("AssertSpecial", "1", {"flag": "noshadow"})
    st.add("PlayerPush", "1", {"value": 0})
    st.add("VelSet", "Time = 0", {"x": 7, "y": 0})
    st.add("VelAdd", "1", {"x": 0.25})
    hit = hitdef("H", 40, attr="S, HP", sparkxy="0,0", spark="S6020", extra={"pausetime": "0, 30",
                                                                              "ground.hittime": 40})
    st.add("HitDef", "Time = 0", hit)
    st.add("ChangeState", ["MoveContact", "Time > 80", "FrontEdgeDist < -40"], {"value": 7101})
    st = c.state(7101, "Lotus detonation (helper)", type="A", movetype="A", physics="N", anim=6142, ctrl=0,
                 sprpriority=6, velset="0,0")
    st.add("AssertSpecial", "1", {"flag": "noshadow"})
    st.add("PlayerPush", "1", {"value": 0})
    st.add("PlaySnd", "Time = 0", snd(3, 5))
    st.add("EnvShake", "Time = 0", {"time": 50, "ampl": 12, "freq": 50})
    st.add("BGPalFX", "Time = 0", {"time": 30, "add": "120, 120, 80", "mul": "256, 256, 256"})
    boom = hitdef("H", 50, attr="S, HP", guard="MA", sparkxy="0,0", spark="S6020", chip=8,
                  extra={"ground.hittime": 30, "air.velocity": "-3,-4", "ground.velocity": "-3"})
    st.add("HitDef", [("Time >= 0", "Time <= 32", "Time % 8 = 0")], boom)
    fin = hitdef("H", 120, attr="S, HP", fall=True, sparkxy="0,0", spark="S6020",
                 extra={"ground.velocity": "-12,-10", "air.velocity": "-12,-10", "fall.recover": 0})
    st.add("HitDef", "Time = 40", fin, label="final blast")
    st.add("DestroySelf", "AnimTime = 0")


def rising_state(c, no, aid, dmg=80, fxanim=None, sndid=(3, 2), up=-15, fwd=3, nhits=2):
    st = c.state(no, "Rising strike", type="S", movetype="A", physics="N", juggle=4, ctrl=0, anim=aid,
                 velset="0,0", sprpriority=2, poweradd=40)
    rise = c.E(aid, "rise")
    st.add("NotHitBy", "AnimElemNo(0) < %d" % (rise + 2), {"value": "SCA", "time": 1})
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("PlaySnd", "AnimElem = %d" % rise, snd(*sndid))
    st.add("VelSet", "AnimElem = %d" % rise, {"x": fwd, "y": up})
    st.add("StateTypeSet", "AnimElem = %d" % rise, {"statetype": "A", "physics": "A"})
    if fxanim:
        st.add("Explod", "AnimElem = %d" % rise, fx_explod(fxanim, "10, 0", extra={"bindtime": 12}))
    h = hitdef("H", dmg // nhits, attr="S, SA", sparkxy="0,-160", spark="S6020",
               extra={"air.velocity": "-2,-9", "ground.velocity": "-2,-9", "fall": 1, "air.fall": 1,
                      "air.juggle": 2})
    st.add("HitDef", "AnimElem = %d" % rise, h)
    st.add("HitDef", [("MoveHit", "AnimElemTime(%d) = 6" % rise)], h, label="second hit")
    st.add("VelAdd", "Vel Y < 20 && AnimElemTime(%d) > 0" % rise, {"y": 0.9})
    st.add("ChangeState", [("Vel Y > 0", "Pos Y >= -2", "AnimElemTime(%d) > 2" % rise)], {"value": 52})
    return st


def teleport_state(c, no, aid, dist=200, sndid=(3, 3), fxanim=None):
    st = c.state(no, "Teleport", type="S", movetype="I", physics="S", ctrl=0, anim=aid, velset="0,0",
                 sprpriority=2)
    out, inn = c.E(aid, "out"), c.E(aid, "in")
    st.add("PlaySnd", "AnimElem = %d" % out, snd(*sndid))
    if fxanim:
        st.add("Explod", "AnimElem = %d" % out, fx_explod(fxanim, "0, 0"))
    st.add("NotHitBy", "AnimElemNo(0) >= %d" % out, {"value": "SCA", "time": 1})
    st.add("AssertSpecial", "AnimElemNo(0) = %d" % out, {"flag": "invisible"})
    st.add("Width", "1", {"value": "0, 0"})
    st.add("PosAdd", "AnimElem = %d" % inn,
           {"x": "ifelse(var(2) = 1, P2Dist X + 70, %d)" % dist})
    st.add("Turn", [("AnimElem = %d" % inn, "var(2) = 1")], {})
    if fxanim:
        st.add("Explod", "AnimElem = %d" % inn, fx_explod(fxanim, "0, 0"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    return st


def moves_yaolao(c):
    proj_state(c, 1000, 1000, projanim=6200, hitanim=6201, vel=(8, 0), dmg=65, name="Bone Chilling Flame",
               sndid=(3, 0), extra={"palfx.time": 40, "palfx.add": "0, 60, 160", "palfx.mul": "180, 220, 256",
                                    "ground.hittime": 24, "pausetime": "14, 18"})
    # 1100 Soul Shock: unblockable short-range soul wave
    st = c.state(1100, "Soul Realm shock", type="S", movetype="A", physics="S", ctrl=0, anim=1100,
                 velset="0,0", juggle=4, poweradd=40, sprpriority=2)
    sp = c.E(1100, "spawn")
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("Explod", "AnimElem = %d" % c.E(1100, "charge"), fx_explod(6010, "8, -170", extra={"scale": "0.6,0.6"}))
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 1))
    st.add("Explod", "AnimElem = %d" % sp, fx_explod(6210, "80, -120"))
    st.add("HitDef", "AnimElem = %d" % sp, hitdef(
        "H", 75, attr="S, SA", guard="", sparkxy="0,-120", spark="S6020", fall=True,
        extra={"ground.velocity": "-7,-5", "air.velocity": "-7,-5", "palfx.time": 30,
               "palfx.add": "40, 120, 160", "palfx.sinadd": "60,60,60,8"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 1200 Alchemy pill: heal
    st = c.state(1200, "Advanced Alchemy: healing pill", type="S", movetype="I", physics="S", ctrl=0, anim=1200,
                 velset="0,0", sprpriority=2)
    st.add("PowerAdd", "Time = 0", {"value": -500})
    st.add("Explod", "AnimElem = %d" % c.E(1200, "refine"), fx_explod(6220, "45, -120", extra={"removetime": 30}))
    st.add("PlaySnd", "AnimElem = %d" % c.E(1200, "eat"), snd(3, 2))
    st.add("LifeAdd", "AnimElem = %d" % c.E(1200, "eat"), {"value": 90})
    st.add("Explod", "AnimElem = %d" % c.E(1200, "eat"), fx_explod(6221, "0, 0"))
    st.add("PalFX", "AnimElem = %d" % c.E(1200, "eat"), {"time": 30, "add": "40,90,30", "sinadd": "40,40,40,10"})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    teleport_state(c, 1300, 1300, sndid=(3, 3), fxanim=6250)
    # 3000 Bone Chilling Flame torrent (beam)
    st = c.state(3000, "Bone Chilling Flame torrent", type="S", movetype="A", physics="S", ctrl=0, anim=3000,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    sp = c.E(3000, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 4))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7200, 7200, "60, -130", name="Frost beam"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    beam = hitdef("M", 22, attr="S, HP", sparkxy="0,0", spark="S6020", chip=3,
                  extra={"ground.hittime": 16, "ground.velocity": "-1.5", "air.velocity": "-1.5,-2",
                         "palfx.time": 20, "palfx.add": "0, 50, 150"})
    helper_state(c, 7200, 6230, 60, hit=beam, every=6, nhits=9, first=2, name="Frost beam (helper)",
                 extra_ctrls=[("HitDef", "Time = 58", hitdef("H", 40, attr="S, HP", fall=True, spark="S6020",
                                                             sparkxy="0,0",
                                                             extra={"ground.velocity": "-9,-6",
                                                                    "air.velocity": "-9,-6"}), None,
                               "final")])
    # 3100 Soul Realm Domination: giant spectral palm crashes down on the opponent
    st = c.state(3100, "Soul Realm domination", type="S", movetype="A", physics="S", ctrl=0, anim=3100,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 2000)
    sp = c.E(3100, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 5))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7210, 7210, "0, 0", postype="p2", name="Soul palm",
                                                  extra={"pos": "0, 0"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    palm = hitdef("H", 160, attr="S, HP", guard="", fall=True, sparkxy="0,-60", spark="S6020",
                  extra={"ground.velocity": "-4,-4", "air.velocity": "-4,-4", "fall.recover": 0,
                         "pausetime": "0, 20"})
    helper_state(c, 7210, 6240, 32, hit=palm, first=18, name="Soul palm (helper)", shake=24,
                 extra_ctrls=[("Explod", "Time = 18", fx_explod(6241, "0, -40")), ])


def moves_xuner(c):
    proj_state(c, 1000, 1000, projanim=6300, hitanim=6301, vel=(7, 0), dmg=70, name="Emperor Seal: Open Mountain",
               sndid=(3, 0), hits=2, misstime=8)
    rising_state(c, 1100, 1100, dmg=100, fxanim=6310, sndid=(3, 1), nhits=2)
    # 1200 Ocean Reversal: somersault overhead kick
    st = c.state(1200, "Emperor Seal: Ocean Reversal", type="S", movetype="A", physics="N", juggle=4, ctrl=0,
                 anim=1200, velset="0,0", sprpriority=2, poweradd=40)
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("PlaySnd", "Time = 3", snd(3, 2))
    st.add("VelSet", "Time = 3", {"x": 6, "y": -12})
    st.add("StateTypeSet", "Time = 3", {"statetype": "A", "physics": "A"})
    st.add("HitDef", "AnimElem = %d" % c.E(1200, "kick"), hitdef(
        "H", 85, attr="A, SA", guard="HA", fall=True, sparkxy="0,-60", spark="S6020",
        extra={"ground.velocity": "-4,-8", "air.velocity": "-4,-8"}))
    st.add("ChangeState", [("Vel Y > 0", "Pos Y >= -2", "Time > 6")], {"value": 52})
    # 3000 Emperor Seal Skill: five seals (Open Mountain, Ocean Reversal, Enveloping Earth, Submerging Sky,
    # Ancient Emperor)
    st = c.state(3000, "Emperor Seal Skill - five seals", type="S", movetype="A", physics="S", ctrl=0,
                 anim=3000, velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    st.add("VelSet", "AnimElem = 2", {"x": 4})
    st.add("VelSet", "AnimElem = %d" % c.E(3000, "final"), {"x": 0})
    for i in range(5):
        e = c.E(3000, "hit%d" % i)
        trig = "AnimElem = %d" % e if i == 0 else [("AnimElem = %d" % e, "MoveHit")]
        h = hitdef("M", 36, attr="S, HA", sparkxy="0,-130", spark="S6020", chip=5,
                   extra={"ground.hittime": 26, "ground.velocity": "-2", "air.velocity": "-2,-3",
                          "hitsound": "S3,3", "pausetime": "6, 10"})
        st.add("HitDef", trig, h, label="seal %d" % (i + 1))
        st.add("Explod", [("AnimElem = %d" % e, "MoveHit || %d = 0" % i)],
               fx_explod(6320, "90, -125", extra={"scale": "0.55,0.55", "removetime": 14}))
    fin = c.E(3000, "final")
    st.add("HitDef", [("AnimElem = %d" % fin, "MoveHit")], hitdef(
        "H", 140, attr="S, HA", fall=True, sparkxy="0,-130", spark="S6020",
        extra={"ground.velocity": "-11,-7", "air.velocity": "-11,-7", "hitsound": "S3,3", "fall.recover": 0}),
        label="Ancient Emperor seal")
    st.add("Explod", [("AnimElem = %d" % fin, "MoveHit")], fx_explod(6320, "110, -125", extra={"scale": "1.2,1.2"}))
    st.add("EnvShake", [("AnimElem = %d" % fin, "MoveHit")], {"time": 30, "ampl": 8, "freq": 60})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 3100 Golden Emperor Burning Heaven Flame
    st = c.state(3100, "Golden Emperor Burning Heaven Flame", type="S", movetype="A", physics="S", ctrl=0,
                 anim=3100, velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 2000)
    sp = c.E(3100, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 4))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7300, 7300, "0, 0", postype="p2", name="Golden pillar",
                                                  extra={"pos": "0, 0"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    pil = hitdef("M", 30, attr="S, HP", sparkxy="0,-150", spark="S6020", chip=4,
                 extra={"ground.hittime": 18, "ground.velocity": "0", "air.velocity": "0,-3", "air.juggle": 0})
    helper_state(c, 7300, 6330, 70, hit=pil, every=8, nhits=7, first=4, name="Golden pillar (helper)", shake=60,
                 extra_ctrls=[("HitDef", "Time = 62", hitdef("H", 80, attr="S, HP", fall=True, spark="S6020",
                                                             sparkxy="0,-150",
                                                             extra={"ground.velocity": "-3,-14",
                                                                    "air.velocity": "-3,-14"}), None, "launch")])


def moves_medusa(c):
    proj_state(c, 1000, 1000, projanim=6400, hitanim=6401, vel=(8, 0), dmg=75, hits=3, misstime=6,
               name="Venomous Flame", sndid=(3, 0),
               extra={"palfx.time": 50, "palfx.add": "60, 0, 90", "palfx.sinadd": "40,0,40,10"})
    # 1100 Serpent lunge
    st = c.state(1100, "Serpent lunge", type="S", movetype="A", physics="S", juggle=4, ctrl=0, anim=1100,
                 velset="0,0", sprpriority=2, poweradd=40)
    go = c.E(1100, "go")
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("PlaySnd", "AnimElem = %d" % go, snd(3, 1))
    st.add("VelSet", "AnimElem = %d" % go, {"x": 14})
    st.add("AfterImage", "AnimElem = %d" % go, {"time": 14, "length": 6, "trans": "add",
                                               "palcontrast": "160, 60, 200"})
    st.add("HitDef", "AnimElem = %d" % go, hitdef("H", 85, attr="S, SA", fall=True, sparkxy="0,-130",
                                                    spark="S6020",
                                                    extra={"ground.velocity": "-8,-5", "air.velocity": "-8,-5"}))
    st.add("VelMul", "AnimElemTime(%d) > 8" % go, {"x": 0.7})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 1200 Spatial seal: traps the opponent in place
    st = c.state(1200, "Spatial seal", type="S", movetype="A", physics="S", juggle=4, ctrl=0, anim=1200,
                 velset="0,0", sprpriority=2, poweradd=40)
    sp = c.E(1200, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 2))
    st.add("Explod", "AnimElem = %d" % sp, fx_explod(6410, "120, -110"))
    st.add("HitDef", "AnimElem = %d" % sp, {**hitdef(
        "M", 40, attr="S, SA", sparkxy="0,-110", spark="S6020",
        extra={"ground.hittime": 60, "ground.slidetime": 0, "ground.velocity": "0", "air.velocity": "0,0",
               "air.hittime": 60, "palfx.time": 60, "palfx.add": "60, 0, 90", "palfx.sinadd": "30,0,30,6",
               "pausetime": "4, 12"})})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 3000 Seven-Coloured Sky Swallowing Python
    st = c.state(3000, "Seven-Coloured Sky Swallowing Python", type="S", movetype="A", physics="S", ctrl=0,
                 anim=3000, velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    sp = c.E(3000, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 3))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7400, 7400, "40, -100", name="Python"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    py = hitdef("M", 26, attr="S, HP", sparkxy="0,0", spark="S6020", chip=4,
                extra={"ground.hittime": 16, "ground.velocity": "4", "air.velocity": "4,-2"})
    helper_state(c, 7400, 6420, 70, hit=py, every=7, nhits=8, first=2, vel=(11, 0), name="Python (helper)",
                 shake=50,
                 extra_ctrls=[("HitDef", "Time = 60", hitdef("H", 70, attr="S, HP", fall=True, spark="S6020",
                                                             sparkxy="0,0",
                                                             extra={"ground.velocity": "6,-10",
                                                                    "air.velocity": "6,-10"}), None, "final")])
    # 3100 Spatial collapse: seal space around the foe and crush it
    st = c.state(3100, "Spatial collapse", type="S", movetype="A", physics="S", ctrl=0, anim=3100,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 2000)
    sp = c.E(3100, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 4))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7410, 7410, "0, -100", postype="p2", name="Collapse",
                                                  extra={"pos": "0, -100"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    col = hitdef("M", 30, attr="S, HP", sparkxy="0,0", spark="S6020", chip=4,
                 extra={"ground.hittime": 20, "ground.velocity": "0", "air.velocity": "0,0", "air.hittime": 20})
    helper_state(c, 7410, 6430, 44, hit=col, every=6, nhits=6, first=2, name="Collapse (helper)", shake=40,
                 extra_ctrls=[("HitDef", "Time = 40", hitdef("H", 110, attr="S, HP", fall=True, spark="S6020",
                                                             sparkxy="0,0",
                                                             extra={"ground.velocity": "-6,-9",
                                                                    "air.velocity": "-6,-9",
                                                                    "fall.recover": 0}), None, "crush")])


def moves_yunyun(c):
    # 1000 Wind blade (sword slash + crescent)
    st = c.state(1000, "Wind Blade", type="S", movetype="A", physics="S", juggle=4, ctrl=0, anim=1000,
                 velset="0,0", sprpriority=2, poweradd=40)
    e = c.E(1000, "hit0")
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("PlaySnd", "AnimElem = %d" % e, snd(3, 0))
    p = {"projid": 1000, "projanim": 6500, "projhitanim": 6501, "projremanim": 6501, "projcancelanim": 6501,
         "projremove": 1, "projremovetime": -1, "velocity": "11, 0", "offset": "80, -120", "projpriority": 1,
         "projhits": 1, "projsprpriority": 4, "projshadow": "0,0,0"}
    p.update(hitdef("M", 60, attr="S, SP", sparkxy="0,0", spark="S6020"))
    st.add("Projectile", "AnimElem = %d" % e, p)
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    rising_state(c, 1100, 1100, dmg=96, fxanim=6510, sndid=(3, 1), nhits=3, up=-14)
    st = c.states[-1]
    st.add("HitDef", [("MoveHit", "AnimElemTime(%d) = 12" % c.E(1100, "rise"))],
           hitdef("H", 32, attr="S, SA", spark="S6020", sparkxy="0,-160", fall=True,
                  extra={"air.velocity": "-3,-9", "ground.velocity": "-3,-9"}), label="third hit")
    teleport_state(c, 1200, 1200, sndid=(3, 2), fxanim=6501)
    # 3000 Wind Lightning sword storm
    st = c.state(3000, "Wind Lightning Pavilion: sword storm", type="S", movetype="A", physics="S", ctrl=0,
                 anim=3000, velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    st.add("PlaySnd", "AnimElem = %d" % c.E(3000, "hit0"), snd(3, 3))
    st.add("VelSet", "AnimElem = 1", {"x": 5})
    st.add("VelSet", "AnimElem = %d" % c.E(3000, "final"), {"x": 0})
    for i in range(6):
        e = c.E(3000, "hit%d" % i)
        trig = "AnimElem = %d" % e if i == 0 else [("AnimElem = %d" % e, "MoveHit")]
        st.add("HitDef", trig, hitdef("M", 30, attr="S, HA", sparkxy="0,-130", spark="S6020", chip=4,
                                      extra={"ground.hittime": 22, "ground.velocity": "-1.5",
                                             "air.velocity": "-1.5,-3", "hitsound": "S3,0",
                                             "pausetime": "5, 8"}), label="slash %d" % (i + 1))
    fin = c.E(3000, "final")
    st.add("Helper", [("AnimElem = %d" % fin, "MoveHit")], helper(c, 7500, 7500, "90, 0", name="Tornado"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    tor = hitdef("M", 20, attr="S, HP", sparkxy="0,-120", spark="S6020", chip=3,
                 extra={"ground.hittime": 14, "ground.velocity": "0,-3", "air.velocity": "0,-4"})
    helper_state(c, 7500, 6520, 50, hit=tor, every=6, nhits=7, first=0, vel=(2, 0), name="Tornado (helper)",
                 sndid=(3, 3),
                 extra_ctrls=[("HitDef", "Time = 46", hitdef("H", 60, attr="S, HP", fall=True, spark="S6020",
                                                             sparkxy="0,-120",
                                                             extra={"ground.velocity": "-6,-10",
                                                                    "air.velocity": "-6,-10"}), None, "final")])
    # 3100 Thousand wind swords
    st = c.state(3100, "Thousand Wind Swords", type="S", movetype="A", physics="S", ctrl=0, anim=3100,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 2000)
    sp = c.E(3100, "spawn")
    for i, dx in enumerate((-90, 0, 90, -45, 45, 0)):
        st.add("Helper", "AnimElemTime(%d) = %d" % (sp, i * 6),
               helper(c, 7510, 7510, "%d, -420" % dx, postype="p2", name="Wind sword"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    sw = hitdef("H", 34, attr="S, HP", sparkxy="0,-20", spark="S6020", chip=4,
                extra={"ground.hittime": 20, "ground.velocity": "0", "air.velocity": "0,3", "hitsound": "S3,4"})
    st = helper_state(c, 7510, 6530, 60, hit=sw, first=0, vel=(0, 16), name="Falling wind sword (helper)",
                      sndid=(3, 4))
    st.ctrls.insert(-1, ("DestroySelf", "Pos Y >= 0", {}, None, "hit the ground"))


def moves_fairydoctor(c):
    proj_state(c, 1000, 1000, projanim=6600, hitanim=6601, vel=(4, 0), dmg=60, hits=4, misstime=12,
               name="Poison Mist", sndid=(3, 0), removetime=120, offset=(80, -110), priority=1,
               extra={"palfx.time": 40, "palfx.add": "50, 0, 70", "palfx.mul": "200,180,220"})
    # 1100 Toxic palm
    st = c.state(1100, "Toxic palm", type="S", movetype="A", physics="S", juggle=4, ctrl=0, anim=1100,
                 velset="0,0", sprpriority=2, poweradd=40)
    go = c.E(1100, "go")
    st.add("PlaySnd", "Time = 1", snd(0, 2, 0))
    st.add("VelSet", "AnimElem = %d" % go, {"x": 9})
    st.add("VelMul", "AnimElemTime(%d) > 6" % go, {"x": 0.7})
    st.add("HitDef", "AnimElem = %d" % go, hitdef(
        "H", 80, attr="S, SA", sparkxy="0,-130", spark="S6601",
        extra={"hitsound": "S3,1", "palfx.time": 60, "palfx.add": "50, 0, 70", "palfx.sinadd": "30,0,30,10",
               "ground.velocity": "-7", "air.velocity": "-6,-5"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    # 1200 Poison field (area denial): lingering mist on the ground ahead
    st = c.state(1200, "Poison field", type="S", movetype="A", physics="S", juggle=4, ctrl=0, anim=1200,
                 velset="0,0", sprpriority=2, poweradd=40)
    sp = c.E(1200, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 2))
    st.add("Helper", [("AnimElem = %d" % sp, "NumHelper(7600) = 0")],
           helper(c, 7600, 7600, "150, -30", name="Poison field"))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    fld = hitdef("L", 18, attr="S, SP", guard="L", sparkxy="0,-30", spark="S6601", chip=2,
                 extra={"ground.hittime": 12, "palfx.time": 30, "palfx.add": "50, 0, 70", "ground.type": "Low"})
    helper_state(c, 7600, 6610, 180, hit=fld, every=24, nhits=7, first=10, name="Poison field (helper)")
    # 3000 Woeful Poison Body unleashed
    st = c.state(3000, "Woeful Poison Body unleashed", type="S", movetype="A", physics="S", ctrl=0, anim=3000,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 1000)
    b = c.E(3000, "burst")
    st.add("PlaySnd", "AnimElem = %d" % b, snd(3, 3))
    st.add("Helper", "AnimElem = %d" % b, helper(c, 7610, 7610, "40, -120", name="Poison body"))
    st.add("NotHitBy", "AnimElemNo(0) >= %d" % b, {"value": "SCA", "time": 1})
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    aur = hitdef("M", 22, attr="S, HP", sparkxy="0,-60", spark="S6601", chip=3,
                 extra={"ground.hittime": 16, "ground.velocity": "-2", "air.velocity": "-2,-3",
                        "palfx.time": 30, "palfx.add": "50, 0, 70"})
    helper_state(c, 7610, 6620, 64, hit=aur, every=8, nhits=7, first=4, name="Poison body (helper)", shake=40,
                 extra_ctrls=[("HitDef", "Time = 60", hitdef("H", 60, attr="S, HP", fall=True, spark="S6601",
                                                             sparkxy="0,-60",
                                                             extra={"ground.velocity": "-8,-7",
                                                                    "air.velocity": "-8,-7"}), None, "final")])
    # 3100 Poison calamity: toxic rain over the opponent
    st = c.state(3100, "Poison calamity", type="S", movetype="A", physics="S", ctrl=0, anim=3100,
                 velset="0,0", sprpriority=2, juggle=0)
    super_start(st, c, 2000)
    sp = c.E(3100, "spawn")
    st.add("PlaySnd", "AnimElem = %d" % sp, snd(3, 4))
    st.add("Helper", "AnimElem = %d" % sp, helper(c, 7620, 7620, "0, 0", postype="p2", name="Poison rain",
                                                  extra={"pos": "0, 0"}))
    st.add("ChangeState", "AnimTime = 0", {"value": 0, "ctrl": 1})
    rn = hitdef("M", 20, attr="S, HP", guard="HA", sparkxy="0,-100", spark="S6601", chip=3,
                extra={"ground.hittime": 14, "ground.velocity": "0", "air.velocity": "0,1",
                       "palfx.time": 30, "palfx.add": "50, 0, 70"})
    helper_state(c, 7620, 6630, 96, hit=rn, every=8, nhits=11, first=8, name="Poison rain (helper)",
                 extra_ctrls=[("HitDef", "Time = 94", hitdef("H", 70, attr="S, HP", guard="HA", fall=True,
                                                             spark="S6601", sparkxy="0,-100",
                                                             extra={"ground.velocity": "-4,-6",
                                                                    "air.velocity": "-4,-6"}), None, "final")])


def buff_minus2(c):
    """Xiao Yan's Skyfire power-up: var(0) counts down while it lasts."""
    return [
        ("VarAdd", "var(0) > 0", {"var(0)": -1}, "!IsHelper", "Skyfire timer"),
        ("AttackMulSet", "1", {"value": "ifelse(var(0) > 0, 1.35, 1)"}, "!IsHelper", "Skyfire attack up"),
        ("Explod", [("var(0) > 0", "NumExplod(6130) = 0")],
         fx_explod(6130, "0, 0", eid=6130, extra={"bindtime": -1, "removetime": -1, "sprpriority": -1,
                                                  "supermovetime": 9999}), "!IsHelper", "Skyfire aura"),
        ("RemoveExplod", "var(0) <= 0 && NumExplod(6130) > 0", {"ID": 6130}, "!IsHelper", "aura off"),
        ("PalFX", [("var(0) > 0", "GameTime % 20 = 0")], {"time": 10, "add": "20, 50, 30",
                                                          "sinadd": "20,40,20,20"}, "!IsHelper", "glow"),
    ]


# --------------------------------------------------------------------------------------
# commands


CMD_HEAD = """; Commands -------------------------------------------------------------------
; Buttons: x = light punch  y = heavy punch  a = light kick  b = heavy kick
;          z = heavy punch (alt)  c = heavy kick (alt)  s = taunt
[Remap]
x = x
y = y
z = z
a = a
b = b
c = c
s = s

[Defaults]
command.time = 15
command.buffer.time = 1
"""


def commands():
    C = []

    def cmd(name, seq, time=None):
        C.append((name, seq, time))
    for b in ("x", "y", "z"):
        cmd("QCFQCF_" + b, "~D, DF, F, D, DF, F, " + b, 30)
        cmd("QCBQCB_" + b, "~D, DB, B, D, DB, B, " + b, 30)
    for b in ("x", "y", "a", "b"):
        cmd("DP_" + b, "~F, D, DF, " + b, 15)
        cmd("QCF_" + b, "~D, DF, F, " + b, 15)
        cmd("QCB_" + b, "~D, DB, B, " + b, 15)
        cmd("DD_" + b, "~D, D, " + b, 15)
    cmd("FF", "F, F", 10)
    cmd("BB", "B, B", 10)
    cmd("recovery", "x+y", 1)
    cmd("throw", "/F, y", 1)
    cmd("throw", "/B, y", 1)
    for b in "xyzabcs":
        cmd(b, b, 1)
    for n, s in (("holdfwd", "/$F"), ("holdback", "/$B"), ("holdup", "/$U"), ("holddown", "/$D")):
        cmd(n, s, 1)
    out = [CMD_HEAD]
    for name, seq, time in C:
        out.append("[Command]\nname = \"%s\"\ncommand = %s" % (name, seq) + ("\ntime = %d" % time if time else "")
                   + "\n")
    return "\n".join(out)


# special-move table per fighter: (state, command names, power cost, condition comment, extra trigger)
SPECIALS = {
    "xiaoyan": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 3000, "Buddha's Angry Lotus"),
                (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Skyfire Three Mysterious Change"),
                (1200, ["DP_x", "DP_y"], 0, "Rising flame ruler"),
                (1000, ["QCF_x", "QCF_y"], 0, "Octane Blast"),
                (1100, ["QCB_x", "QCB_y"], 0, "Flame Splitting Tsunami")],
    "yaolao": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 2000, "Soul Realm domination"),
               (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Bone Chilling Flame torrent"),
               (1200, ["DD_x", "DD_y"], 500, "Healing pill"),
               (1000, ["QCF_x", "QCF_y"], 0, "Bone Chilling Flame"),
               (1100, ["QCB_x", "QCB_y"], 0, "Soul shock"),
               (1300, ["QCB_a", "QCB_b"], 0, "Spirit drift")],
    "xuner": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 2000, "Golden Emperor Burning Heaven Flame"),
              (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Emperor Seal Skill"),
              (1100, ["DP_x", "DP_y"], 0, "Golden flame rise"),
              (1000, ["QCF_x", "QCF_y"], 0, "Open Mountain seal"),
              (1200, ["QCB_a", "QCB_b"], 0, "Ocean Reversal")],
    "medusa": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 2000, "Spatial collapse"),
               (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Seven-Coloured Python"),
               (1200, ["DD_x", "DD_y"], 0, "Spatial seal"),
               (1000, ["QCF_x", "QCF_y"], 0, "Venomous Flame"),
               (1100, ["QCB_x", "QCB_y"], 0, "Serpent lunge")],
    "yunyun": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 2000, "Thousand Wind Swords"),
               (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Sword storm"),
               (1100, ["DP_x", "DP_y"], 0, "Rising gale"),
               (1000, ["QCF_x", "QCF_y"], 0, "Wind blade"),
               (1200, ["QCB_a", "QCB_b"], 0, "Wind step")],
    "fairydoctor": [(3100, ["QCBQCB_x", "QCBQCB_y", "QCBQCB_z"], 2000, "Poison calamity"),
                    (3000, ["QCFQCF_x", "QCFQCF_y", "QCFQCF_z"], 1000, "Woeful Poison Body"),
                    (1200, ["DD_x", "DD_y"], 0, "Poison field"),
                    (1000, ["QCF_x", "QCF_y"], 0, "Poison mist"),
                    (1100, ["QCB_x", "QCB_y"], 0, "Toxic palm")],
}

PROJECTILE_STATES = {"xiaoyan": 1100, "yaolao": 1000, "xuner": 1000, "medusa": 1000, "yunyun": 1000,
                     "fairydoctor": 1000}
ANTIAIR = {"xiaoyan": 1200, "xuner": 1100, "yunyun": 1100}
RUSH = {"xiaoyan": 1000, "medusa": 1100, "fairydoctor": 1100, "yaolao": 1100, "xuner": 1200, "yunyun": 3000}


def minus1(key):
    st = St(-1, "Command -> state")
    cancel = "(StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))"
    st.add("VarSet", "1", {"var(1)": "command = \"QCF_y\" || command = \"QCB_y\" || command = \"DP_y\""},
           label="strong version flag")
    for no, cmds, cost, label in SPECIALS[key]:
        trig = [("command = \"%s\"" % cmd,) for cmd in cmds]
        al = [cancel]
        if cost:
            al.append("Power >= %d" % cost)
        if key == "yunyun" and no == 1200 or key == "yaolao" and no == 1300:
            st.add("VarSet", trig, {"var(2)": "P2BodyDist X < 140"}, all=al, label="teleport side")
        if key == "fairydoctor" and no == 1200:
            al.append("NumHelper(7600) = 0")
        st.add("ChangeState", trig, {"value": no}, all=al, label=label)
    # throw
    st.add("ChangeState", [("command = \"throw\"", "StateType = S", "Ctrl", "P2BodyDist X < 20",
                            "P2StateType != A", "P2MoveType != H")], {"value": 800}, label="Throw")
    # normals with chain cancels
    def norm(no, btn, stype, chain=None):
        trig = [("command = \"%s\"" % btn, "Ctrl")]
        if chain:
            trig.append(("command = \"%s\"" % btn, "StateNo = [%d, %d]" % chain, "MoveContact"))
        al = ["StateType = %s" % stype] if stype != "A" else ["StateType = A"]
        if stype == "S":
            al.append("command != \"holddown\"")
        elif stype == "C":
            al = ["command = \"holddown\"", "StateType != A"]
        return trig, al
    for no, btn, stype, chain in (
            (210, "y", "S", (200, 209)), (210, "z", "S", (200, 209)), (200, "x", "S", None),
            (240, "b", "S", (200, 239)), (240, "c", "S", (200, 239)), (230, "a", "S", None),
            (410, "y", "C", (400, 409)), (410, "z", "C", (400, 409)), (400, "x", "C", None),
            (440, "b", "C", (400, 439)), (440, "c", "C", (400, 439)), (430, "a", "C", None),
            (610, "y", "A", None), (610, "z", "A", None), (600, "x", "A", None),
            (640, "b", "A", None), (640, "c", "A", None), (630, "a", "A", None)):
        trig, al = norm(no, btn, stype, chain)
        st.add("ChangeState", trig, {"value": no}, all=al)
    st.add("ChangeState", [("command = \"s\"", "StateType = S", "Ctrl")], {"value": 195}, label="Taunt")
    st.add("ChangeState", [("command = \"FF\"", "StateType = S", "Ctrl")], {"value": 100}, label="Run")
    st.add("ChangeState", [("command = \"BB\"", "StateType = S", "Ctrl")], {"value": 105}, label="Hop back")
    return st


def ai_block(key):
    """Simple CPU logic (only active when the engine sets AILevel > 0)."""
    st = []
    al = ["AILevel > 0", "RoundState = 2", "Ctrl", "StateType != A"]
    sp = {s[0]: s for s in SPECIALS[key]}
    for no, cmds, cost, label in SPECIALS[key]:
        if no >= 3000:
            st.append(("ChangeState", [("Power >= %d" % cost, "P2BodyDist X < %d" % (150 if no in (3000,) else 260),
                                        "P2MoveType != A || Random < 300",
                                        "Random < AILevel * 6")], {"value": no}, al, "AI super"))
    if key in ANTIAIR:
        st.append(("ChangeState", [("P2StateType = A", "P2BodyDist X < 90", "P2Dist Y < -40",
                                    "Random < AILevel * 60")], {"value": ANTIAIR[key]}, al, "AI anti-air"))
    pj = PROJECTILE_STATES[key]
    st.append(("ChangeState", [("P2BodyDist X > 160", "NumProjID(%d) = 0" % pj, "Random < AILevel * 8")],
               {"value": pj}, al, "AI zoning"))
    if key in RUSH:
        rn = RUSH[key]
        if rn < 3000:
            st.append(("ChangeState", [("P2BodyDist X = [40, 180]", "P2MoveType != A", "Random < AILevel * 5")],
                       {"value": rn}, al, "AI rush"))
    if key == "yaolao":
        st.append(("ChangeState", [("Life < 500", "Power >= 500", "P2BodyDist X > 220",
                                    "Random < AILevel * 10")], {"value": 1200}, al, "AI heal"))
    if key == "fairydoctor":
        st.append(("ChangeState", [("P2BodyDist X = [100, 220]", "NumHelper(7600) = 0",
                                    "Random < AILevel * 4")], {"value": 1200}, al, "AI field"))
    st.append(("ChangeState", [("P2BodyDist X < 30", "P2StateType != A", "P2MoveType != H",
                                "Random < AILevel * 6")], {"value": 800}, al, "AI throw"))
    for no, dist, rnd in ((200, 60, 30), (230, 70, 25), (210, 90, 20), (240, 100, 18), (430, 70, 12),
                          (440, 95, 10), (410, 70, 6)):
        st.append(("ChangeState", [("P2BodyDist X < %d" % dist, "P2StateType != L", "Random < AILevel * %d" % (rnd // 6 + 1))],
                   {"value": no}, al, "AI normal %d" % no))
    st.append(("ChangeState", [("StateNo = [200, 249]", "MoveHit", "AnimTime = 0", "Random < AILevel * 100")],
               {"value": RUSH.get(key, pj) if RUSH.get(key, pj) < 3000 else pj},
               ["AILevel > 0", "RoundState = 2"], "AI combo"))
    st.append(("ChangeState", [("P2StateType = A", "P2BodyDist X < 60", "Random < AILevel * 20")],
               {"value": 410}, al, "AI anti-air normal"))
    return st


# --------------------------------------------------------------------------------------
# file writers

DATA = """[Data]
life = 1000
power = 3000
attack = 100
defence = {defence}
fall.defence_up = 50
liedown.time = 60
airjuggle = 15
sparkno = 2
guard.sparkno = 40
KO.echo = 0
volume = 0
IntPersistIndex = 60
FloatPersistIndex = 40

[Size]
xscale = 1
yscale = 1
ground.back = 30
ground.front = 32
air.back = 24
air.front = 24
height = 120
attack.dist = 320
proj.attack.dist = 180
proj.doscale = 0
head.pos = -10, -190
mid.pos = -10, -120
shadowoffset = 0
draw.offset = 0, 0

[Velocity]
walk.fwd = {walk}
walk.back = -{walkb}
run.fwd = 9.2, 0
run.back = -9, -7.6
jump.neu = 0, -16.8
jump.back = -5.1
jump.fwd = 5
runjump.back = -5.1, -16.2
runjump.fwd = 8, -16.2
airjump.neu = 0, -16.2
airjump.back = -5.1
airjump.fwd = 5

[Movement]
airjump.num = {airjumps}
airjump.height = 70
yaccel = {yaccel}
stand.friction = .85
crouch.friction = .82
stand.friction.threshold = 4
crouch.friction.threshold = .1
air.gethit.groundlevel = 50
air.gethit.groundrecover.ground.threshold = -40
air.gethit.groundrecover.groundlevel = 20
air.gethit.airrecover.threshold = -2
air.gethit.airrecover.yaccel = .7
air.gethit.trip.groundlevel = 30
down.bounce.offset = 0, 40
down.bounce.yaccel = .8
down.bounce.groundlevel = 24
down.friction.threshold = .1
"""

STATS = {
    "xiaoyan": dict(defence=100, walk=4.8, walkb=4.4, airjumps=1, yaccel=0.88),
    "yaolao": dict(defence=92, walk=4.2, walkb=4.2, airjumps=2, yaccel=0.78),
    "xuner": dict(defence=108, walk=5.0, walkb=4.6, airjumps=1, yaccel=0.86),
    "medusa": dict(defence=100, walk=5.0, walkb=4.6, airjumps=1, yaccel=0.88),
    "yunyun": dict(defence=96, walk=5.6, walkb=5.2, airjumps=2, yaccel=0.84),
    "fairydoctor": dict(defence=94, walk=4.4, walkb=4.2, airjumps=1, yaccel=0.86),
}

MOVELIST = {
    "xiaoyan": [("Octane Blast (Ba Ji Beng)", "QCF + P", "Dashing palm that detonates up to eight times"),
                ("Flame Splitting Tsunami", "QCB + P", "Heavy Profound Ruler slam sends a wave of flame along the ground"),
                ("Rising Flame Ruler", "F, D, DF + P", "Invincible anti-air ruler swing"),
                ("Skyfire Three Mysterious Change", "QCF, QCF + P (1 bar)", "Burst + 10 s attack buff with flame aura"),
                ("Buddha's Angry Lotus", "QCB, QCB + P (3 bars)", "Compressed multi-flame lotus that detonates")],
    "yaolao": [("Bone Chilling Flame", "QCF + P", "Freezing white flame projectile"),
               ("Soul Shock", "QCB + P", "Unblockable soul-wave that bypasses guard"),
               ("Advanced Alchemy: Healing Pill", "D, D + P (half bar)", "Refines and eats a pill to restore life"),
               ("Spirit Drift", "QCB + K", "Ghostly teleport (behind the foe when close)"),
               ("Bone Chilling Flame Torrent", "QCF, QCF + P (1 bar)", "Multi-hit frost beam"),
               ("Soul Realm Domination", "QCB, QCB + P (2 bars)", "Unblockable giant soul palm crashes on the foe")],
    "xuner": [("Emperor Seal: Open Mountain", "QCF + P", "Golden seal projectile"),
              ("Golden Flame Rise", "F, D, DF + P", "Invincible rising golden flame"),
              ("Emperor Seal: Ocean Reversal", "QCB + K", "Somersault overhead kick"),
              ("Emperor Seal Skill", "QCF, QCF + P (1 bar)", "Five-seal combo ending with Ancient Emperor"),
              ("Golden Emperor Burning Heaven Flame", "QCB, QCB + P (2 bars)", "Pillar of golden flame under the foe"),
              ("Bloodline Suppression", "passive", "Higher defence")],
    "medusa": [("Venomous Flame", "QCF + P", "Three-hit poisonous flame"),
               ("Serpent Lunge", "QCB + P", "Fast lunging strike"),
               ("Spatial Seal", "D, D + P", "Seals space and freezes the foe in place"),
               ("Seven-Coloured Sky Swallowing Python", "QCF, QCF + P (1 bar)", "Rainbow python charges across the screen"),
               ("Spatial Collapse", "QCB, QCB + P (2 bars)", "Crushing vortex around the foe")],
    "yunyun": [("Wind Blade", "QCF + P", "Sword slash that throws a wind crescent"),
               ("Rising Gale", "F, D, DF + P", "Spinning anti-air slash"),
               ("Wind Step", "QCB + K", "Wind Lightning Pavilion teleport"),
               ("Sword Storm", "QCF, QCF + P (1 bar)", "Six slashes ending in a tornado"),
               ("Thousand Wind Swords", "QCB, QCB + P (2 bars)", "Wind swords rain down on the foe")],
    "fairydoctor": [("Poison Mist", "QCF + P", "Slow, lingering four-hit toxic cloud"),
                    ("Toxic Palm", "QCB + P", "Stepping poisonous palm"),
                    ("Poison Field", "D, D + P", "Area denial: poison pools on the ground for 3 seconds"),
                    ("Woeful Poison Body", "QCF, QCF + P (1 bar)", "Invincible toxic mist explosion"),
                    ("Poison Calamity", "QCB, QCB + P (2 bars)", "Miasma rain over the foe")],
}


def build_char(key, name, anims, fx):
    c = Ctx(key, name, anims, fx)
    build_common(c, DESIGN_FLAGS[key])
    {"xiaoyan": moves_xiaoyan, "yaolao": moves_yaolao, "xuner": moves_xuner, "medusa": moves_medusa,
     "yunyun": moves_yunyun, "fairydoctor": moves_fairydoctor}[key](c)
    extra = []
    if key == "xiaoyan":
        extra = buff_minus2(c)
    if key == "yaolao":
        extra = [("Trans", "1", {"trans": "addalpha", "alpha": "210, 90"}, "!IsHelper", "ghostly body")]
    if key == "fairydoctor":
        extra = [("Explod", [("GameTime % 40 = 0", "StateNo = 0", "Random < 500")],
                  fx_explod(6600, "%d, -60" % 0, extra={"scale": "0.35,0.35", "removetime": 30, "vel": "0, -0.5",
                                                         "sprpriority": -2, "trans": "addalpha",
                                                         "alpha": "120, 200"}), "!IsHelper",
                  "toxic mist aura")]
    m2 = St(-2, "Always-run logic")
    base = build_minus2(c, None)
    for (typ, trig, p, al, label) in base.ctrls:
        m2.ctrls.append((typ, trig, p, al, label))
    for e in extra:
        typ, trig, p, al, label = e
        m2.ctrls.append((typ, trig, p, al, label))
    cns = [DATA.format(**STATS[key]), "", "; ---------------- states ----------------", ""]
    for s in c.states:
        cns.append(s.text())
    cns.append(m2.text())
    # cmd file
    cmd = [commands(), "", "; ---------------- command -> state ----------------", "[Statedef -1]", ""]
    m1 = minus1(key)
    ai = ai_block(key)
    body = m1.text().split("\n", 2)[2]  # drop header lines
    ai_txt = St(-1)
    for (typ, trig, p, al, label) in ai:
        ai_txt.add(typ, trig, p, all=al, label=label)
    cmd.append("; CPU (only when AILevel > 0)")
    cmd.append(ai_txt.text().split("\n", 1)[1])
    cmd.append("; Player commands")
    cmd.append(body)
    return "\n".join(cns), "\n".join(cmd)


DESIGN_FLAGS = {}


def def_file(key, name, author="BTTH 2.5D fan project"):
    return """; {name} - Battle Through the Heavens 2.5D (fan-made, non-commercial)
[Info]
name = "{name}"
displayname = "{name}"
versiondate = 10,26,2026
mugenversion = 1.1
author = "{author}"
pal.defaults = 1,2,3,4,5,6
localcoord = 640, 480

[Files]
cmd = {key}.cmd
cns = {key}.cns
stcommon = common1.cns
sprite = {key}.sff
anim = {key}.air
sound = {key}.snd

[Arcade]
""".format(key=key, name=name, author=author)
