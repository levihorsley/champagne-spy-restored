#!/usr/bin/env python3
"""Stillness check per frame n: worst-block mean |blur(T_n) - blur(T_{n+1})| and the same for bottom fields
(same-parity fields, so no half-line offset; blur removes grain). ~0 = nothing moved between frames n and n+1.
Usage: staticdiff_all.py SOURCE.mkv OUT.npy  -> shape (2, N): ST, SB (last frame = 999)"""
import sys, numpy as np, vapoursynth as vs
c = vs.core; src = c.bs.VideoSource(sys.argv[1])
def box(a, k=7):
    r = k // 2; p = np.pad(a, ((r + 1, r), (r + 1, r)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:, k:] - p[:-k, k:] - p[k:, :-k] + p[:-k, :-k]) / (k * k)
def worst(a, b):
    d = np.abs(a - b)[8:-8, 8:-8]; h, w = d.shape[0] // 16 * 16, d.shape[1] // 32 * 32
    return d[:h, :w].reshape(h // 16, 16, w // 32, 32).mean(axis=(1, 3)).max()
N = src.num_frames; out = np.full((2, N), 999, np.float32); prev = None
for n, f in enumerate(src.frames(close=True)):
    y = np.asarray(f[0]).astype(np.float32); T, B = box(y[0::2]), box(y[1::2])
    if prev is not None: out[0, n-1] = worst(prev[0], T); out[1, n-1] = worst(prev[1], B)
    prev = (T, B)
    if n % 25000 == 0: print("…", n, flush=True)
np.save(sys.argv[2], out); print("done", flush=True)
