#!/usr/bin/env python3
"""Detector #2, calibrated like TIVTC IsCombed: CombMask(cthresh=9), then the densest 16x16 block's combed-pixel count
(scattered grain can't fill a block; real combing along a moving edge does). Also logs overall fraction.
Usage: comb_blocks.py SOURCE.mkv OUT.csv"""
import sys, numpy as np, vapoursynth as vs
src, out = sys.argv[1], sys.argv[2]
c = vs.core
clip = c.bs.VideoSource(src)
mask = c.vszip.CombMask(clip, cthresh=9, mthresh=9)
H, Wd = clip.height, clip.width
with open(out, "w") as f:
    f.write("frame,frac,blockmax\n")
    for n, fr in enumerate(mask.frames(close=True)):
        m = (np.asarray(fr[0]) > 0)
        b = m[:H // 16 * 16, :Wd // 16 * 16].reshape(H // 16, 16, Wd // 16, 16).sum(axis=(1, 3))
        f.write(f"{n},{m.mean():.5f},{int(b.max())}\n")
        if n % 25000 == 0: print("…", n, flush=True)
print("done", flush=True)
