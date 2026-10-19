#!/usr/bin/env python3
"""Motion-order check on the FINISHED film: decode once, mean |difference| between consecutive output frames
(luma, 1/4 size). In a 50 fps video shot the step from frame to frame should be even. If a shot's field order were
wrong, time would run 1,0,3,2,...: steps alternate short/long (1 field vs 3 fields). Per shot: ratio of the larger
alternating-position mean to the smaller, ignoring near-zero steps (repeated film frames are expected: 0,X,0,X)."""
import sys, json, numpy as np, vapoursynth as vs
c = vs.core; E = c.bs.VideoSource(sys.argv[1]); small = c.resize.Bilinear(E, 180, 144, format=vs.GRAY8)
N = small.num_frames; d = np.zeros(N, np.float32); prev = None
for n, f in enumerate(small.frames(close=True)):
    y = np.asarray(f[0]).astype(np.float32)
    if prev is not None: d[n] = np.abs(y - prev).mean()
    prev = y
np.save("final_build/verify/film_framediff.npy", d)
shots = json.load(open("scripts/main_shots_interlace.json")); rows = []
for s in shots:
    a, b = 2 * s["start"] + 1, 2 * s["end"]
    if b - a < 40: continue
    x = d[a:b]; even, odd = x[0::2], x[1::2]
    me, mo = even[even > 0.3].mean() if (even > 0.3).any() else 0, odd[odd > 0.3].mean() if (odd > 0.3).any() else 0
    if min(me, mo) < 0.8: continue                        # too little motion to judge
    rows.append((max(me, mo) / min(me, mo), s["start"], s["end"], s["bucket"][:28], round(me, 2), round(mo, 2)))
rows.sort(reverse=True)
print("shots with enough motion:", len(rows))
print("worst alternation ratios (1.0 = perfectly even; wrong field order would give ~3):")
for r in rows[:12]: print(f"  ratio {r[0]:.2f}  frames {r[1]}-{r[2]}  {int(r[1]/25//60)}:{r[1]/25%60:04.1f}  {r[3]}  even {r[4]} odd {r[5]}")
print("ratio > 1.5:", sum(1 for r in rows if r[0] > 1.5), "| > 2.0:", sum(1 for r in rows if r[0] > 2.0))
