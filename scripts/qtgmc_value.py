#!/usr/bin/env python3
"""Where does a full QTGMC rebuild add value? For every 50p slot, compare
  A = the plan (exact disc picture where a same-instant field exists, QTGMC exact-lines mode elsewhere)
  B = QTGMC 'clean' rebuild of every field (Placebo, SourceMatch=3, Lossless=2, default temporal smoothing)
Per slot and picture, luma only, 8 px border ignored, flat (black/blank) 16x16 blocks ignored:
  lp   = share of blocks with an alternating-line pattern (adjacent-line difference clearly above same-field
         2-line difference; real images do the opposite, plain noise is ~equal)
  lpe  = mean excess adjacent-line energy (size of that pattern)
  hd   = horizontal detail (mean |x - x+2px|; interlacing never touches horizontal detail, so a drop = smoothing)
  v2   = vertical detail at 2-line scale
  tn   = temporal change vs the previous slot of the same picture type (noise/flicker indicator)
  dab  = mean |A - B| and dmax = worst 16x16 block of |A - B| (how much QTGMC changes the picture)
Output scripts/main_qtgmc_value.npy  shape (2N, 12): lpA lpeA hdA v2A tnA lpB lpeB hdB v2B tnB dab dmax"""
import os, sys, runpy, numpy as np, vapoursynth as vs
W = os.path.expanduser("~/Movies/ChampagneSpy_work")
g = runpy.run_path(f"{W}/scripts/main_50p.vpy")
c = vs.core; import havsfunc as haf
o = vs.get_output(0); A = o[0] if isinstance(o, tuple) else o
clip, tff, prog = g["clip"], g["tff"], g["prog"]
def qc(t): return prog(haf.QTGMC(c.std.SetFieldBased(clip, 2 if t else 1), Preset="Placebo", TFF=t, FPSDivisor=1,
                                SourceMatch=3, Lossless=2, NoiseProcess=0))
QT, QB = qc(True), qc(False)
B = c.std.FrameEval(g["own"], lambda n: QT if tff[n] else QB)
S = 2 * clip.num_frames
def blocks(a, k=16):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))
def metrics(y, prev):
    y = y[8:-8, 8:-8]
    d1 = np.abs(y[1:-1] - y[2:]); d2 = np.abs(y[:-2] - y[2:])
    n1, n2 = blocks(d1), blocks(d2); sd = blocks(np.abs(y[1:-1] - blocks(y[1:-1], 16).repeat(16, 0).repeat(16, 1)[:y.shape[0]-2, :y.shape[1]]) if False else d2)
    live = (n2 + n1) > 1.0                                    # skip flat blocks
    lp = float(((n1 > 1.15 * n2 + 0.3) & (n1 > 1.5) & live).sum() / max(live.sum(), 1))
    lpe = float(np.maximum(n1 - n2, 0)[live].mean()) if live.any() else 0.0
    hd = float(np.abs(y[:, 2:] - y[:, :-2]).mean()); v2 = float(d2.mean())
    tn = float(np.abs(y - prev[8:-8, 8:-8]).mean()) if prev is not None else 0.0
    return [lp, lpe, hd, v2, tn]
out = np.zeros((S, 12), np.float32); pa = pb = None
for n, (fa, fb) in enumerate(zip(A.frames(close=True), B.frames(close=True))):
    a = np.asarray(fa[0]).astype(np.float32); b = np.asarray(fb[0]).astype(np.float32)
    d = np.abs(a - b)
    out[n] = metrics(a, pa) + metrics(b, pb) + [float(d.mean()), float(blocks(d[8:-8, 8:-8]).max())]
    pa, pb = a, b
    if n % 10000 == 0:
        print("…", n, "of", S, flush=True); np.save(f"{W}/scripts/main_qtgmc_value.partial.npy", out[:n+1])
np.save(f"{W}/scripts/main_qtgmc_value.npy", out); print("done", flush=True)
