#!/usr/bin/env python3
"""Cross-frame field differences (grain-proof blurred, as detector #3) for every frame n:
  tb[n] = |B_n - T_{n+1}|   (TFF: 2nd field of n vs 1st field of n+1)
  bt[n] = |T_n - B_{n+1}|   (BFF equivalent)
With in-frame |T_n - B_n| (main_fielddiff.npy) this lets every field pick its true partner.
Usage: crossdiff_all.py SOURCE.mkv OUT.npy"""
import sys, numpy as np, vapoursynth as vs
c = vs.core; src = c.bs.VideoSource(sys.argv[1])
def box(a, k=7):
    p = np.pad(a, ((k, k), (k, k)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:-k, k:-k] - p[:-2*k, k:-k] - p[k:-k, :-2*k] + p[:-2*k, :-2*k])[k//2:k//2+a.shape[0], k//2:k//2+a.shape[1]] / (k*k)
N = src.num_frames; tb = np.zeros(N, np.float32); bt = np.zeros(N, np.float32)
prev = None
for n, f in enumerate(src.frames(close=True)):
    y = np.asarray(f[0]).astype(np.float32); T, B = box(y[0::2]), box(y[1::2])
    if prev is not None:
        pT, pB = prev
        tb[n-1] = np.mean(np.abs(pB - T)[8:-8, 8:-8]); bt[n-1] = np.mean(np.abs(pT - B)[8:-8, 8:-8])
    prev = (T, B)
    if n % 25000 == 0: print("…", n, flush=True)
tb[-1] = bt[-1] = 999
np.save(sys.argv[2], np.stack([tb, bt])); print("done", flush=True)
