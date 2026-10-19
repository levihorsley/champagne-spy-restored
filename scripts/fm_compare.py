#!/usr/bin/env python3
"""For given slots: crop of (a) chosen weave, (b) QTGMC Placebo output for the same slot, (c) the other weave candidate.
If (a) looks like (b) the line pattern is in the source fields themselves (weave is the exact original);
if (a) shows teeth that (b) lacks, the weave is wrong. Usage: fm_compare.py OUT.png frame:slot:partner ..."""
import sys, os, numpy as np, vapoursynth as vs
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__)); from fm_common import load
c = vs.core
for p in ("vsznedi3.so", "libfmtconv.dylib", "libremovegrain.dylib"): c.std.LoadPlugin(os.path.expanduser("~/Movies/ChampagneSpy_work/vsplugins/") + p)
import havsfunc as haf
d = load(); clip = c.bs.VideoSource(os.path.expanduser("~/Movies/ChampagneSpy_work/main_source.mkv"))
def cross(tff):
    src = c.std.SetFieldBased(clip, 2 if tff else 1)
    return c.std.SelectEvery(c.std.DoubleWeave(c.std.SeparateFields(src, tff=tff), tff=tff), 2, 1)
V = {"C": clip, "X": cross(True), "Y": cross(False)}; M = {k: c.vszip.CombMask(v, cthresh=9, mthresh=9) for k, v in V.items()}
F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15, index=1)
def get(n, part, tff):
    k, i = ("C", n) if part == "in" else (("X" if tff else "Y"), n - 1 if part == "prev" else n)
    return np.asarray(V[k].get_frame(i)[0]), np.asarray(M[k].get_frame(i)[0]) > 0
rows = []
for spec in sys.argv[2:]:
    n, slot, part = spec.split(":"); n, slot = int(n), int(slot); tff = bool(d["tff"][n])
    w, m = get(n, part, tff)
    alt = ("prev" if slot % 2 == 0 else "next") if part == "in" else "in"; wa, _ = get(n, alt, tff)
    seg = c.std.SetFieldBased(clip[n-12:n+13], 2 if tff else 1)
    q = haf.QTGMC(seg, Preset="Placebo", TFF=tff, FPSDivisor=1, SourceMatch=3, Lossless=2, NoiseProcess=0)
    qa = np.asarray(q.get_frame(24 + slot % 2)[0])
    H, W = w.shape; b = m[:H//16*16, :W//16*16].reshape(H//16, 16, W//16, 16).sum(axis=(1, 3))
    by, bx = np.unravel_index(b.argmax(), b.shape); y0, x0 = min(max(by*16+8-48, 0), H-96), min(max(bx*16+8-64, 0), W-128)
    tiles = [Image.fromarray(a[y0:y0+96, x0:x0+128]).resize((384, 288), Image.NEAREST).convert("RGB") for a in (w, qa, wa)]
    row = Image.new("RGB", (3*388, 288+22), (20, 20, 20))
    for i, t in enumerate(tiles): row.paste(t, (i*388, 22))
    ImageDraw.Draw(row).text((4, 3), f"frame {n} slot {slot}:  A = chosen weave ({part})   |   B = QTGMC   |   C = rejected weave ({alt})", font=F, fill=(255, 210, 80))
    rows.append(row)
S = Image.new("RGB", (3*388, len(rows)*314), (0, 0, 0))
for i, r in enumerate(rows): S.paste(r, (0, i*314))
S.save(sys.argv[1]); print("saved")
