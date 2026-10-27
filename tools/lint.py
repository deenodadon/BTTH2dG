#!/usr/bin/env python3
"""Static validator for the generated MUGEN/Ikemen content.

Checks every character and stage for: missing files, sprite/animation/sound references,
AnimElem numbers past the end of an animation, unknown state controllers / parameters /
trigger names (tables extracted from Ikemen GO's compiler, see extract_ikemen_names.py),
unbalanced expressions, undefined commands and missing target states.

usage: python3 tools/lint.py            (exit code 1 on any error)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sffv2 import read_sff  # noqa: E402
from snd import read_snd  # noqa: E402

NAMES = json.load(open(os.path.join(HERE, "ikemen_names.json")))
SCTRLS = {k: set(v) for k, v in NAMES["sctrls"].items()}
TRIGGERS = set(NAMES["triggers"])
COMMON_PARAMS = {"type", "persistent", "ignorehitpause", "redirectid", "triggerall"}
COMMON_STATES = {0, 10, 11, 12, 20, 40, 45, 50, 51, 52, 100, 105, 106, 110, 115, 120, 130, 131, 132, 140, 150, 151,
                 152, 153, 154, 155, 170, 175, 190, 191, 5000, 5001, 5010, 5011, 5020, 5030, 5035, 5040, 5050, 5070,
                 5071, 5080, 5081, 5100, 5101, 5110, 5120, 5150, 5200, 5201, 5210, 5500, 5900}
KEYWORDS = {"var", "fvar", "sysvar", "sysfvar", "const", "ifelse", "cond", "abs", "and", "or", "not", "x", "y", "z",
            "command", "s", "f", "hit", "miss", "a", "c", "l", "h", "i", "n", "u", "e", "pi", "random"}

errors = []
warnings = []


def err(where, msg):
    errors.append("%s: %s" % (where, msg))


def warn(where, msg):
    warnings.append("%s: %s" % (where, msg))


def ini_sections(text):
    """Yield (header, [(key, value, lineno)]) with ';' comments stripped."""
    sec, items = None, []
    for no, line in enumerate(text.splitlines(), 1):
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            if sec is not None:
                yield sec, items
            sec, items = line.strip("[]").strip(), []
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            items.append((k.strip().lower(), v.strip(), no))
        else:
            items.append((line.lower(), None, no))
    if sec is not None:
        yield sec, items


def parse_air(text, where):
    actions = {}
    cur = None
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"\[Begin Action (-?\d+)\]", line, re.I)
        if m:
            cur = int(m.group(1))
            if cur in actions:
                err(where, "duplicate action %d" % cur)
            actions[cur] = []
            continue
        if cur is None:
            continue
        low = line.lower()
        if low.startswith("clsn") or low.startswith("loopstart"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5:
            try:
                actions[cur].append((int(parts[0]), int(parts[1]), int(parts[4])))
            except ValueError:
                err("%s:%d" % (where, no), "bad frame line: %s" % line)
    return actions


def check_expr(expr, where, commands, animset):
    if expr.count("(") != expr.count(")"):
        err(where, "unbalanced parentheses: %s" % expr)
    if expr.count('"') % 2:
        err(where, "unbalanced quotes: %s" % expr)
    for cmd in re.findall(r'command\s*!?=\s*"([^"]+)"', expr, re.I):
        if cmd not in commands:
            err(where, "unknown command \"%s\"" % cmd)
    stripped = re.sub(r'"[^"]*"', "", expr)
    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", stripped):
        low = ident.lower()
        if low in TRIGGERS or low in KEYWORDS:
            continue
        if re.fullmatch(r"[sf]\d+", low):
            continue
        warn(where, "unknown identifier %s in %s" % (ident, expr))


def check_char(key):
    base = os.path.join(ROOT, "game", "chars", key)
    where0 = "chars/%s" % key
    deftext = open(os.path.join(base, key + ".def")).read()
    files = {}
    for sec, items in ini_sections(deftext):
        if sec.lower() == "files":
            for k, v, _ in items:
                files[k] = v
    for k in ("cmd", "cns", "sprite", "anim", "sound"):
        if not files.get(k) or not os.path.exists(os.path.join(base, files[k])):
            err(where0, "def: missing %s file %s" % (k, files.get(k)))
    pals, sprites = read_sff(os.path.join(base, files["sprite"]))
    palkeys = [p[0] for p in pals]
    for i in range(1, 7):
        if (1, i) not in palkeys:
            err(where0, "missing palette 1,%d" % i)
    for (g, n) in ((9000, 0), (9000, 1)):
        if (g, n) not in sprites:
            err(where0, "missing portrait sprite %d,%d" % (g, n))
    sounds = read_snd(os.path.join(base, files["sound"]))
    air = parse_air(open(os.path.join(base, files["anim"])).read(), where0 + "/air")
    for aid, frs in air.items():
        if not frs:
            err(where0, "action %d has no frames" % aid)
        for g, n, t in frs:
            if (g, n) not in sprites and g >= 0:
                err(where0, "action %d references missing sprite %d,%d" % (aid, g, n))
    # common states that wait for these animations to end (AnimTime = 0): a -1 last frame freezes them
    for a in (5, 6, 10, 12, 40, 47, 120, 190, 5035, 5100, 5120, 5170):
        if a in air and air[a] and air[a][-1][2] == -1:
            err(where0, "animation %d ends on an infinite (-1) frame but the common state waits for it to finish" % a)
    required = [0, 5, 6, 10, 11, 12, 20, 21, 40, 41, 42, 43, 47, 100, 105, 120, 130, 131, 132, 150, 151, 152, 170,
                180, 190, 5000, 5001, 5002, 5010, 5011, 5012, 5020, 5021, 5022, 5030, 5035, 5040, 5050, 5070, 5080,
                5090, 5100, 5110, 5120, 5140, 5150, 5160, 5170, 5200, 5210, 5300]
    for a in required:
        if a not in air:
            err(where0, "required animation %d missing" % a)

    # commands
    cmdtext = open(os.path.join(base, files["cmd"])).read()
    commands = set()
    for sec, items in ini_sections(cmdtext):
        if sec.lower() == "command":
            for k, v, _ in items:
                if k == "name":
                    commands.add(v.strip('"'))
    for c in ("holdfwd", "holdback", "holdup", "holddown", "recovery"):
        if c not in commands:
            err(where0, "required command %s missing" % c)

    # states
    states = {}
    blocks = []
    # Ikemen GO only compiles states from st/stN files and the cmd file ("cns" is constants only)
    st_files = [v for k, v in files.items() if re.fullmatch(r"st\d*", k) and v]
    if not st_files:
        err(where0, "def: no st file, so none of the character's own states would load")
    for fname in st_files + [files["cmd"]]:
        text = open(os.path.join(base, fname)).read()
        cur = None
        for sec, items in ini_sections(text):
            m = re.match(r"statedef\s+(-?\d+)", sec, re.I)
            if m:
                cur = int(m.group(1))
                hdr = {k: v for k, v, _ in items}
                if cur in states and cur >= 0:
                    err(where0, "duplicate statedef %d" % cur)
                states[cur] = hdr
                continue
            if re.match(r"state\s+", sec, re.I):
                blocks.append((fname, cur, sec, items))
    allstates = set(states) | COMMON_STATES
    for no, hdr in states.items():
        if "anim" in hdr and int(hdr["anim"]) not in air:
            err(where0, "statedef %d uses missing anim %s" % (no, hdr["anim"]))
    for fname, sno, sec, items in blocks:
        where = "%s/%s [%s]" % (where0, fname, sec)
        p = {}
        trig_nums = set()
        for k, v, ln in items:
            if k.startswith("trigger"):
                if k != "triggerall":
                    try:
                        trig_nums.add(int(k[7:]))
                    except ValueError:
                        err(where, "bad trigger key %s" % k)
                check_expr(v or "", where, commands, air)
            else:
                p[k] = v
        typ = (p.get("type") or "").lower()
        if typ not in SCTRLS:
            err(where, "unknown controller type %s" % typ)
            continue
        if not trig_nums:
            err(where, "no trigger1")
        elif sorted(trig_nums) != list(range(1, max(trig_nums) + 1)):
            err(where, "triggers not numbered contiguously: %s" % sorted(trig_nums))
        known = SCTRLS[typ] | COMMON_PARAMS
        for k in p:
            if k not in known and len(SCTRLS[typ]) > 3 and not k.startswith("var(") and not k.startswith("fvar("):
                warn(where, "parameter %s not in Ikemen's %s parser" % (k, typ))
        # references
        st_anim = states.get(sno, {}).get("anim")
        if st_anim is not None and any(k.startswith("trigger") and re.search(r"AnimTime\s*=\s*0\b", v or "", re.I)
                                       for k, v, ln in items):
            frs = air.get(int(st_anim), [])
            if frs and frs[-1][2] == -1:
                err(where, "waits for AnimTime = 0 but anim %s ends on an infinite (-1) frame" % st_anim)
        for k, v, ln in items:
            if k.startswith("trigger") and st_anim is not None:
                for n in re.findall(r"AnimElem\s*=\s*(\d+)", v, re.I) + re.findall(r"AnimElem(?:Time|No)\((\d+)\)", v, re.I):
                    nf = len(air.get(int(st_anim), []))
                    if int(n) > nf:
                        err(where, "AnimElem %s beyond anim %s (%d frames)" % (n, st_anim, nf))
        if typ in ("changestate", "selfstate") and p.get("value", "").lstrip("-").isdigit():
            if int(p["value"]) not in allstates:
                err(where, "ChangeState to undefined state %s" % p["value"])
        if typ == "targetstate" and p.get("value", "").isdigit() and int(p["value"]) not in allstates:
            err(where, "TargetState to undefined state %s" % p["value"])
        if typ == "helper" and int(p.get("stateno", 0)) not in states:
            err(where, "helper stateno %s undefined" % p.get("stateno"))
        if typ in ("changeanim", "changeanim2") and p.get("value", "").isdigit() and int(p["value"]) not in air:
            err(where, "ChangeAnim to missing anim %s" % p["value"])
        for k in ("anim", "projanim", "projhitanim", "projremanim", "projcancelanim"):
            v = p.get(k)
            if v and v.lstrip("-").isdigit() and int(v) >= 0 and typ in ("explod", "projectile") and int(v) not in air:
                err(where, "%s %s missing" % (k, v))
        for k in ("sparkno", "guard.sparkno"):
            v = p.get(k, "")
            if v.upper().startswith("S") and int(v[1:]) not in air:
                err(where, "%s %s missing in AIR" % (k, v))
        if typ == "playsnd":
            v = p.get("value", "")
            if not v.upper().startswith("F"):
                g, n = [int(x) for x in v.split(",")]
                if (g, n) not in sounds:
                    err(where, "sound %d,%d missing" % (g, n))
        for k in ("hitsound", "guardsound"):
            v = p.get(k, "")
            if v.upper().startswith("S"):
                g, n = [int(x) for x in v[1:].split(",")]
                if (g, n) not in sounds:
                    err(where, "%s %s missing" % (k, v))
        if typ == "superpause" and p.get("sound", "").upper().startswith("S"):
            g, n = [int(x) for x in p["sound"][1:].split(",")]
            if (g, n) not in sounds:
                err(where, "superpause sound missing")
    return dict(sprites=len(sprites), anims=len(air), states=len(states), sounds=len(sounds))


def check_stage(sid):
    base = os.path.join(ROOT, "game", "stages")
    where = "stages/%s" % sid
    text = open(os.path.join(base, sid + ".def")).read()
    spr = None
    for sec, items in ini_sections(text):
        if sec.lower() == "bgdef":
            spr = dict((k, v) for k, v, _ in items).get("spr")
    if not spr or not os.path.exists(os.path.join(base, spr)):
        err(where, "missing sff %s" % spr)
        return {}
    _, sprites = read_sff(os.path.join(base, spr))
    air = parse_air(text, where)
    for aid, frs in air.items():
        for g, n, t in frs:
            if (g, n) not in sprites:
                err(where, "action %d sprite %d,%d missing" % (aid, g, n))
    for sec, items in ini_sections(text):
        if sec.lower().startswith("bg ") and sec.lower() != "bgdef":
            d = {k: v for k, v, _ in items}
            if "spriteno" in d:
                g, n = [int(x) for x in d["spriteno"].split(",")]
                if (g, n) not in sprites:
                    err(where, "[%s] sprite %d,%d missing" % (sec, g, n))
            if d.get("type") == "anim" and int(d.get("actionno", -1)) not in air:
                err(where, "[%s] action missing" % sec)
    return dict(sprites=len(sprites))


def main():
    chars_dir = os.path.join(ROOT, "game", "chars")
    sel = open(os.path.join(ROOT, "game", "data", "select.def")).read()
    for sec, items in ini_sections(sel):
        if sec.lower() == "characters":
            for k, v, _ in items:
                path = k.split(",")[0].strip()
                if not os.path.exists(os.path.join(chars_dir, path)):
                    err("select.def", "character %s not found" % path)
                for part in (k + ("," + v if v else "")).split(",")[1:]:
                    part = part.strip()
                    if part.startswith("stages/") and not os.path.exists(os.path.join(ROOT, "game", part)):
                        err("select.def", "stage %s not found" % part)
    for key in sorted(os.listdir(chars_dir)):
        info = check_char(key)
        print("char  %-12s %s" % (key, info))
    for f in sorted(os.listdir(os.path.join(ROOT, "game", "stages"))):
        if f.endswith(".def"):
            print("stage %-12s %s" % (f[:-4], check_stage(f[:-4])))
    seen = set()
    for w in warnings:
        if w not in seen:
            print("WARN ", w)
            seen.add(w)
    for e in errors:
        print("ERROR", e)
    print("%d errors, %d warnings" % (len(errors), len(seen)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
