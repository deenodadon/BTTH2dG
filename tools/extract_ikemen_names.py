#!/usr/bin/env python3
"""Extract state-controller, parameter and trigger names from an Ikemen GO source tree.

usage: python3 tools/extract_ikemen_names.py /path/to/Ikemen-GO/src > tools/ikemen_names.json
The JSON is used by tools/lint.py to validate the generated CNS/CMD files."""
import json
import re
import sys


def main(src):
    comp = open(src + "/compiler.go").read()
    funcs = open(src + "/compiler_functions.go").read()
    m = re.search(r"c\.scmap = map\[string\]scFunc\{(.*?)\n\t\}", comp, re.S)
    scmap = dict(re.findall(r'"(\w+)":\s*c\.(\w+),', m.group(1)))
    bodies = {}
    for text in (funcs, comp):
        for fm in re.finditer(r"^func \(c \*CharCompiler\) (\w+)\(", text, re.M):
            name = fm.group(1)
            start = fm.end()
            nxt = text.find("\nfunc ", start)
            bodies.setdefault(name, text[start:nxt if nxt > 0 else len(text)])

    def params(fn, seen):
        if fn in seen or fn not in bodies:
            return set()
        seen.add(fn)
        b = bodies[fn]
        out = set(s.lower() for s in re.findall(r'"([A-Za-z0-9_.]+)"', b))
        for callee in re.findall(r"c\.(\w+)\(", b):
            out |= params(callee, seen)
        for callee, prefix in re.findall(r'c\.(\w+)\(is, sc, "([A-Za-z0-9_.]+)"', b):
            out |= {prefix.lower() + q for q in params(callee, set())}
        return out
    sc = {k: sorted(params(v, set())) for k, v in scmap.items()}
    trig = set(s.lower() for s in re.findall(r'case "([A-Za-z0-9_.]+)"', comp))
    trig |= set(s.lower() for s in re.findall(r'^\t"([a-z0-9_.]+)":\s*\d+,', comp, re.M))
    json.dump({"sctrls": sc, "triggers": sorted(trig)}, sys.stdout, indent=0, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1])
