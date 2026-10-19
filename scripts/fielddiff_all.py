#!/usr/bin/env python3
"""Detector #3 (grain-proof): mean |blurred top field - blurred bottom field| for every frame. Grain averages out;
motion/fades between the two field instants remain. Calibrated: progressive <= ~5.3, interlaced motion >= 6.
Usage: fielddiff_all.py SOURCE.mkv OUT.npy"""
import sys, numpy as np, vapoursynth as vs
c = vs.core; src = c.bs.VideoSource(sys.argv[1])
def box(a, k=7):
    p = np.pad(a, ((k, k), (k, k)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:-k, k:-k] - p[:-2*k, k:-k] - p[k:-k, :-2*k] + p[:-2*k, :-2*k])[k//2:k//2+a.shape[0], k//2:k//2+a.shape[1]] / (k*k)
out = np.zeros(src.num_frames, np.float32)
for n, f in enumerate(src.frames(close=True)):
    y = np.asarray(f[0]).astype(np.float32)
    out[n] = np.mean(np.abs(box(y[0::2]) - box(y[1::2]))[8:-8, 8:-8])
    if n % 25000 == 0: print("…", n, flush=True)
np.save(sys.argv[2], out); print("done", flush=True)
