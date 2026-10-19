#!/usr/bin/env python3
"""Detector #2: per-frame combing (vszip.CombMask marks pixels that are combed AND moving), read frame-accurately
via BestSource. First proves BestSource frame n == ffmpeg frame n (the numbering detector #1 and the master used).
Usage: comb_analysis.py SOURCE.mkv OUT.csv"""
import sys, subprocess, numpy as np, vapoursynth as vs
src, out = sys.argv[1], sys.argv[2]
c = vs.core
clip = c.bs.VideoSource(src)
print(f"bestsource frames={clip.num_frames} fps={clip.fps}", flush=True)
for n in (0, clip.num_frames // 2, clip.num_frames - 1):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", src, "-map", "0:v:0", "-vf", f"select=eq(n\\,{n})",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], capture_output=True).stdout
    ff = np.frombuffer(raw[:clip.width * clip.height], np.uint8).reshape(clip.height, clip.width)
    bs = np.asarray(clip.get_frame(n)[0])
    print(f"frame {n}: bestsource vs ffmpeg max pixel diff = {int(np.abs(ff.astype(int) - bs.astype(int)).max())}", flush=True)
avg = c.vszip.PlaneAverage(c.vszip.CombMask(clip), exclude=[-1], planes=[0])
with open(out, "w") as f:
    f.write("frame,comb\n")
    for n, fr in enumerate(avg.frames(close=True)):
        f.write(f"{n},{fr.props['psmAvg']:.6f}\n")
        if n % 20000 == 0: print("…", n, flush=True)
print("done", flush=True)
