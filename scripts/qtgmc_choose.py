#!/usr/bin/env python3
"""Pick the shots where a full QTGMC rebuild adds value (Levi 2026-10-13: "determine where QTGMC adds value and use it there").
Value = the exact picture still carries an alternating-line pattern (interlaced-video noise / field mismatch baked into
the transfer) that the rebuild removes. Elsewhere the rebuild only removes grain/detail (~15%), so the exact picture stays.
Whole shots only (no look changes mid-shot). Output: main_qtgmc_choice.npy (per 50p slot: 1 = QTGMC rebuild)."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); from fm_common import load
LP_MIN, KEEP_MAX, STILL_MAX = float(sys.argv[1]) if len(sys.argv) > 1 else 0.08, 0.3, 0.5
# never on text: the rebuild ghosts moving/scrolling lettering (seen on the end credits). Source-frame ranges:
TEXT = [(0, 4200), (128750, 129600), (131275, 135587)]   # opening credits to 2:48, epilogue cards, end credits
D = os.path.dirname(__file__); d = load()
v = np.load(f"{D}/main_qtgmc_value.npy") if os.path.exists(f"{D}/main_qtgmc_value.npy") else np.load(f"{D}/main_qtgmc_value.partial.npy")
n = len(v); lpA, lpB, hdA, hdB = v[:, 0], v[:, 5], v[:, 2], v[:, 7]
rule = np.load(f"{D}/main_fieldmatch.npy")[1]
choice = np.zeros(2 * d["N"], np.int8); rows = []
for s in d["shots"]:
    a, b = 2 * s["start"], 2 * s["end"]
    if b > n: continue
    la, lb = lpA[a:b].mean(), lpB[a:b].mean(); still = (rule[a:b] == 4).mean(); keep = np.median(hdB[a:b] / np.maximum(hdA[a:b], 1e-3))
    text = any(s["start"] < b2 and s["end"] > a2 for a2, b2 in TEXT)
    pick = la >= LP_MIN and lb <= KEEP_MAX * la and still < STILL_MAX and not text
    if pick: choice[a:b] = 1
    rows.append(dict(start=s["start"], end=s["end"], lpA=round(float(la), 4), lpB=round(float(lb), 4), still=round(float(still), 3), detail_kept=round(float(keep), 3), pick=bool(pick), text=bool(text), bucket=s["bucket"]))
np.save(f"{D}/main_qtgmc_choice.npy", choice); json.dump(rows, open(f"{D}/main_qtgmc_choice.json", "w"), indent=0)
p = [r for r in rows if r["pick"]]; fr = sum(r["end"] - r["start"] for r in p)
print(f"analysed {n} slots; shots picked for QTGMC rebuild: {len(p)} of {len(rows)} ({fr/25/60:.1f} min of {sum(r['end']-r['start'] for r in rows)/25/60:.1f} min analysed)")
