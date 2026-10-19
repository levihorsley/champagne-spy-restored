#!/usr/bin/env python3
"""Measure exactly when each burned-in German title is visible, frame by frame, for timing the added English lines.
Method: take the title's letter strokes from a frame in the middle of its known appearance (thin bright structures:
pixel brighter than its 15x15 neighbourhood by > 30; yellow titles also need yellow chroma). For every frame in a
window around it, visibility = share of those exact stroke pixels that are strokes again (background baseline removed,
normalised to the title's maximum). On screen = >= 50%. Times in the subtitle (source) timeline: frame n starts 0.04 + n/25."""
import json, numpy as np, vapoursynth as vs
c = vs.core; clip = c.bs.VideoSource("main_source.mkv")
CUES = [("presenters", 82.28, 87.28, "yellow", 0, 400, 120, 340), ("Kamera", 91.2, 94.84, "yellow", 0, 360, 0, 220),
        ("Schnitt", 101.96, 105.6, "yellow", 360, 720, 288, 576), ("Ton", 115.12, 119.72, "yellow", 360, 720, 0, 220),
        ("Visuelle Effekte", 123.24, 128.8, "yellow", 360, 720, 288, 576), ("Originalmusik", 125.16, 128.8, "yellow", 0, 360, 100, 340),
        ("Produzenten", 147.4, 154.44, "yellow", 0, 400, 0, 260), ("Titel", 155.0, 161.72, "yellow", 80, 640, 180, 400),
        ("Buch und Regie", 162.88, 166.52, "yellow", 120, 600, 240, 420), ("Avigdor", 515.84, 523.84, "white", 200, 700, 370, 452),
        ("Arie Sivan", 855.92, 859.28, "white", 250, 690, 370, 462), ("Hannelore", 2072.68, 2078.32, "white", 260, 720, 360, 470),
        ("Rivka", 5152.0, 5160.6, "white", 290, 720, 100, 420), ("Lotz", 5163.2, 5171.8, "white", 290, 720, 100, 420),
        ("Oded", 5174.32, 5182.44, "white", 290, 720, 100, 420)]
def box(a, k=15):
    r = k // 2; p = np.pad(a, ((r + 1, r), (r + 1, r)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:, k:] - p[:-k, k:] - p[k:, :-k] + p[:-k, :-k]) / (k * k)
def strokes(n, kind, x0, x1, y0, y1):
    f = clip.get_frame(n); Y = np.asarray(f[0]).astype(float); m = (Y - box(Y)) > 30
    if kind == "yellow":
        U = np.asarray(f[1]).repeat(2, 0).repeat(2, 1).astype(int); V = np.asarray(f[2]).repeat(2, 0).repeat(2, 1).astype(int)
        m &= (U < 118) & (V > 126)
    return m[y0:y1, x0:x1]
res = {}
for lab, s, e, kind, x0, x1, y0, y1 in CUES:
    mid = int(((s + e) / 2 - 0.04) * 25); T = strokes(mid, kind, x0, x1, y0, y1)
    T &= strokes(mid - 5, kind, x0, x1, y0, y1) & strokes(mid + 5, kind, x0, x1, y0, y1)   # stable strokes only
    n0, n1 = int((s - 0.04 - 4) * 25), int((e - 0.04 + 4) * 25)
    v = np.array([(strokes(n, kind, x0, x1, y0, y1) & T).sum() / max(T.sum(), 1) for n in range(n0, n1)])
    base = np.median(np.r_[v[:20], v[-20:]]); v = (v - base) / max(v.max() - base, 1e-6)
    # contiguous run >= 50% that contains the template frame
    k = mid - n0; on = v >= 0.5; a = k; b = k
    while a > 0 and on[a - 1]: a -= 1
    while b < len(v) - 1 and on[b + 1]: b += 1
    t = lambda i: 0.04 + (n0 + i) / 25
    edge = " (WINDOW EDGE)" if a == 0 or b == len(v) - 1 else ""
    res[lab] = dict(start=round(t(a), 3), end=round(t(b + 1), 3), strokes=int(T.sum()))
    print(f"{lab:17s} strokes {int(T.sum()):5d}  on-screen {t(a):8.2f}–{t(b+1):8.2f}  old {s:8.2f}–{e:8.2f}  start {t(a)-s:+.2f}  end {t(b+1)-e:+.2f}{edge}")
json.dump(res, open("scripts/caption_timing.json", "w"), indent=1)
