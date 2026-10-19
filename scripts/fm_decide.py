#!/usr/bin/env python3
"""Per-field (slot) decision for the 50 fps master. For every field: join it with the neighbouring field that was
captured at the same moment (exact original lines, no interpolation) when the evidence is clear; otherwise QTGMC.
Evidence: L = local grain-proof field difference (main_localdiff.npy) says WHICH neighbour shares the instant;
CombMask block max (combblocks/crossweave) confirms static cases. Output: main_fieldmatch.npy, one code per slot
(0 = QTGMC, 1 = weave with previous field, 2 = weave with own frame's other field, 3 = weave with next field)
plus the rule that fired (for auditing). Usage: fm_decide.py [main|x01..x08]"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from fm_common import load
R, LMAX, CSAFE, LSTATIC, LPROG, STILL = 2.0, 10.0, 32, 3.0, 8.0, 1.0
PROG = {"progressive (both detectors)", "line structure without field motion (grain or baked-in stripes)", "static/undecidable, no visible combing"}
PFX = sys.argv[1] if len(sys.argv) > 1 else "main"
d = load(PFX); N, tff, C, prev, nxt = d["N"], d["tff"], d["C"], d["prev"], d["nxt"]
LC, LX, LY = np.load(os.path.join(os.path.dirname(__file__), f"{PFX}_localdiff.npy"))
Lprev = np.where(tff, np.r_[999, LX[:-1]], np.r_[999, LY[:-1]]); Lnext = np.where(tff, LX, LY)
prog = np.array([b in PROG for b in d["bucket"]])
code = np.zeros(2 * N, np.int8); rule = np.zeros(2 * N, np.int8)
for s in (0, 1):                                   # s=0 first field of frame n (candidates prev|in), s=1 second (in|next)
    Lo, Co, oc = (Lprev, prev, 1) if s == 0 else (Lnext, nxt, 3)
    in_best = LC <= Lo
    Lb, Lw = np.where(in_best, LC, Lo), np.where(in_best, Lo, LC)
    Cb = np.where(in_best, C, Co); cb = np.where(in_best, 2, oc)
    r1 = (Lw >= R * Lb) & (Lb <= LMAX)             # clear same-instant partner
    r2 = ~r1 & (Cb <= CSAFE) & (Lb <= LSTATIC)     # static and clean
    r3 = ~r1 & ~r2 & prog & (LC <= LPROG)          # progressive shot, own frame's fields agree
    c = np.where(r1 | r2, cb, np.where(r3, 2, 0)); ru = np.where(r1, 1, np.where(r2, 2, np.where(r3, 3, 0)))
    code[s::2], rule[s::2] = c, ru
# Rule 4 (overrides): nothing moved (same-parity fields of frames n-1, n, n+1 identical after blur) -> exact own frame.
# Catches still title cards / text, where sharp letter edges otherwise look like field differences.
SP = os.path.join(os.path.dirname(__file__), f"{PFX}_staticdiff.npy")
if os.path.exists(SP):
    ST, SB = np.load(SP); still = np.maximum.reduce([ST, SB, np.r_[999, ST[:-1]], np.r_[999, SB[:-1]]]) <= STILL
    for s in (0, 1): code[s::2] = np.where(still, 2, code[s::2]); rule[s::2] = np.where(still, 4, rule[s::2])
else: print("WARNING: no stillness data for", PFX)
code[0] = 2 if code[0] == 1 else code[0]; code[-1] = 2 if code[-1] == 3 else code[-1]   # film edges
np.save(os.path.join(os.path.dirname(__file__), f"{PFX}_fieldmatch.npy"), np.stack([code, rule]))
bk = np.repeat(d["bucket"], 2)
names = {0: "QTGMC", 1: "weave prev", 2: "weave own", 3: "weave next"}
print(f"{'shot type':42s} {'slots':>7s}  " + "  ".join(f"{names[k]:>10s}" for k in range(4)) + "   rule1  rule2  rule3  still")
for k in sorted(set(d["bucket"])) + ["ALL"]:
    m = np.ones(2 * N, bool) if k == "ALL" else bk == k
    print(f"{k[:42]:42s} {m.sum():7d}  " + "  ".join(f"{(code[m] == c).mean():10.3f}" for c in range(4)) +
          "   " + "  ".join(f"{(rule[m] == r).mean():5.2f}" for r in (1, 2, 3, 4)))
