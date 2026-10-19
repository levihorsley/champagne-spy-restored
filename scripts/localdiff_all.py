#!/usr/bin/env python3
"""Local grain-proof field-motion measure for the three candidate pairs of every frame n:
  C[n] = (T_n, B_n)   X[n] = (B_n, T_{n+1})   Y[n] = (T_n, B_{n+1})
Each field is box-blurred (7x7, kills grain/texture), then mean |difference| per 16x32 field-pixel block
(= 32x32 in the frame); the worst block is stored. Motion between the two field instants stays; texture doesn't.
Usage: localdiff_all.py SOURCE.mkv OUT.npy"""
import sys, numpy as np, vapoursynth as vs
c = vs.core; src = c.bs.VideoSource(sys.argv[1])
def box(a, k=7):
    p = np.pad(a, ((k, k), (k, k)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:-k, k:-k] - p[:-2*k, k:-k] - p[k:-k, :-2*k] + p[:-2*k, :-2*k])[k//2:k//2+a.shape[0], k//2:k//2+a.shape[1]] / (k*k)
def worst(a, b):
    d = np.abs(a - b)[8:-8, 8:-8]; h, w = d.shape[0] // 16 * 16, d.shape[1] // 32 * 32
    return d[:h, :w].reshape(h // 16, 16, w // 32, 32).mean(axis=(1, 3)).max()
N = src.num_frames; out = np.full((3, N), 999, np.float32); prev = None
for n, f in enumerate(src.frames(close=True)):
    y = np.asarray(f[0]).astype(np.float32); T, B = box(y[0::2]), box(y[1::2])
    out[0, n] = worst(T, B)
    if prev is not None:
        pT, pB = prev; out[1, n-1] = worst(pB, T); out[2, n-1] = worst(pT, B)
    prev = (T, B)
    if n % 25000 == 0: print("…", n, flush=True)
np.save(sys.argv[2], out); print("done", flush=True)
