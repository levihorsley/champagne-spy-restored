#!/usr/bin/env python3
"""Detector #2 (CombMask cthresh=9 + densest 16x16 block) on the two CROSS-frame weaves of every frame n:
  X[n] = weave(T_{n+1}, B_n)   -> B_n paired with the NEXT top field   (TFF neighbour)
  Y[n] = weave(T_n, B_{n+1})   -> T_n paired with the NEXT bottom field (BFF neighbour)
With main_combblocks.csv (in-frame weave T_n+B_n) every field can be checked against both neighbours
using a local (block) measure, so small moving objects in otherwise static frames are not missed.
Usage: crossweave_blocks.py SOURCE.mkv OUT.npy"""
import sys, numpy as np, vapoursynth as vs
c = vs.core
clip = c.bs.VideoSource(sys.argv[1])
N, H, Wd = clip.num_frames, clip.height, clip.width
def cross(tff):
    src = c.std.SetFieldBased(clip, 2 if tff else 1)  # source carries a TFF flag that would override tff=
    w = c.std.DoubleWeave(c.std.SeparateFields(src, tff=tff), tff=tff)
    return c.std.SelectEvery(w, 2, 1)            # odd frames = cross pairs; last one is a dangling field
X = c.vszip.CombMask(cross(True), cthresh=9, mthresh=9)
Y = c.vszip.CombMask(cross(False), cthresh=9, mthresh=9)
out = np.full((2, N), 9999, np.int32)
def bmax(fr):
    m = (np.asarray(fr[0]) > 0)
    return int(m[:H // 16 * 16, :Wd // 16 * 16].reshape(H // 16, 16, Wd // 16, 16).sum(axis=(1, 3)).max())
for n, (fx, fy) in enumerate(zip(X.frames(close=True), Y.frames(close=True))):
    if n >= N - 1: break
    out[0, n], out[1, n] = bmax(fx), bmax(fy)
    if n % 25000 == 0: print("…", n, flush=True)
np.save(sys.argv[2], out); print("done", flush=True)
