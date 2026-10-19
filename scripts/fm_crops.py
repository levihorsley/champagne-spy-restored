#!/usr/bin/env python3
"""Render zoomed crops of chosen weaves around their most-combed 16x16 block, for threshold calibration.
Masks are computed exactly as in the full passes (CombMask needs its temporal neighbours for the motion gate).
Usage: fm_crops.py OUT.png 'frame:slot:partner' ...   partner in prev|in|next"""
import sys, os, numpy as np, vapoursynth as vs
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__)); from fm_common import load
d = load(); c = vs.core; clip = c.bs.VideoSource(os.path.expanduser("~/Movies/ChampagneSpy_work/main_source.mkv"))
def cross(tff):
    src = c.std.SetFieldBased(clip, 2 if tff else 1)
    return c.std.SelectEvery(c.std.DoubleWeave(c.std.SeparateFields(src, tff=tff), tff=tff), 2, 1)
V = {"C": clip, "X": cross(True), "Y": cross(False)}
M = {k: c.vszip.CombMask(v, cthresh=9, mthresh=9) for k, v in V.items()}
F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15, index=1)
tiles = []
for spec in sys.argv[2:]:
    n, slot, part = spec.split(":"); n, slot = int(n), int(slot); tff = d["tff"][n]
    k, i = ("C", n) if part == "in" else (("X" if tff else "Y"), n - 1 if part == "prev" else n)
    w = np.asarray(V[k].get_frame(i)[0]); m = np.asarray(M[k].get_frame(i)[0]) > 0
    H, W = w.shape; b = m[:H//16*16, :W//16*16].reshape(H//16, 16, W//16, 16).sum(axis=(1, 3))
    by, bx = np.unravel_index(b.argmax(), b.shape); cy, cx = by*16+8, bx*16+8
    y0, x0 = min(max(cy-48, 0), H-96), min(max(cx-64, 0), W-128)
    crop = Image.fromarray(w[y0:y0+96, x0:x0+128]).resize((384, 288), Image.NEAREST).convert("RGB")
    full = Image.fromarray(w).resize((256, 205)).convert("RGB"); ImageDraw.Draw(full).rectangle([x0*256/W, y0*205/H, (x0+128)*256/W, (y0+96)*205/H], outline="red", width=2)
    t = Image.new("RGB", (384+256+4, 288+22), (20, 20, 20)); t.paste(crop, (0, 22)); t.paste(full, (388, 22))
    ImageDraw.Draw(t).text((4, 3), f"frame {n} slot {slot} weave={part}  blockmax={int(b.max())}  {d['bucket'][n][:28]}", font=F, fill=(255, 210, 80))
    tiles.append(t)
cols = 2; rows = (len(tiles)+1)//2; S = Image.new("RGB", (cols*648, rows*314), (0, 0, 0))
for i, t in enumerate(tiles): S.paste(t, ((i % cols)*648, (i//cols)*314))
S.save(sys.argv[1]); print("saved", sys.argv[1])
