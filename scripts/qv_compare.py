#!/usr/bin/env python3
"""Side-by-side A (plan: exact disc picture / QTGMC exact-lines) vs B (QTGMC clean rebuild) for given source frames,
cropped around the block with the strongest alternating-line pattern in A. Two views: actual TV-size and 3x zoom.
Usage: qv_compare.py OUT.png frame [frame ...]"""
import os, sys, runpy, numpy as np, vapoursynth as vs
from PIL import Image, ImageDraw, ImageFont
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); g = runpy.run_path(f"{W}/scripts/main_50p.vpy")
c = vs.core; import havsfunc as haf
o = vs.get_output(0); A = o[0] if isinstance(o, tuple) else o
clip, tff = g["clip"], g["tff"]; F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16, index=1)
def blocks(a, k=16):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k; return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))
def rgb(clip_, i):
    f = c.resize.Bicubic(clip_[i], format=vs.RGB24, matrix_in=5).get_frame(0); return np.dstack([np.asarray(f[p]) for p in range(3)])
rows = []
for fr in map(int, sys.argv[2:]):
    s = 2 * fr; t = bool(tff[s])
    Bq = haf.QTGMC(c.std.SetFieldBased(clip[fr-12:fr+13], 2 if t else 1), Preset="Placebo", TFF=t, FPSDivisor=1, SourceMatch=3, Lossless=2, NoiseProcess=0)
    a_rgb, b_rgb = rgb(A, s), rgb(Bq, 24)
    y = np.asarray(A.get_frame(s)[0]).astype(float); d1 = np.abs(y[1:-1] - y[2:]); d2 = np.abs(y[:-2] - y[2:])
    ex = blocks(np.maximum(d1 - d2, 0)); by, bx = np.unravel_index(ex.argmax(), ex.shape); cy, cx = by * 16 + 8, bx * 16 + 8
    y0, x0 = min(max(cy - 48, 0), 576 - 96), min(max(cx - 64, 0), 720 - 128)
    row = Image.new("RGB", (2 * 516 + 2 * 388, 30 + 290), (20, 20, 20))
    for k, (arr, lab) in enumerate(((a_rgb, "A exact"), (b_rgb, "B QTGMC rebuild"))):
        tv = Image.fromarray(arr).resize((1024, 576), Image.LANCZOS)
        X0 = int(x0 * 1024 / 720) - 190; X0 = min(max(X0, 0), 1024 - 512); Y0 = min(max(y0 - 96, 0), 576 - 288)
        row.paste(tv.crop((X0, Y0, X0 + 512, Y0 + 288)), (k * 516, 30))
        row.paste(Image.fromarray(arr[y0:y0+96, x0:x0+128]).resize((384, 288), Image.NEAREST), (1032 + k * 388, 30))
        ImageDraw.Draw(row).text((k * 516 + 4, 6), f"{lab}  (TV size)", font=F, fill=(255, 210, 80))
        ImageDraw.Draw(row).text((1032 + k * 388 + 4, 6), f"{lab}  (3x zoom)", font=F, fill=(255, 210, 80))
    ImageDraw.Draw(row).text((4, 300), f"frame {fr}  {int(fr/25//60)}:{fr/25%60:04.1f}", font=F, fill=(200, 200, 200))
    rows.append(row)
S = Image.new("RGB", (rows[0].width, len(rows) * 324)); [S.paste(r, (0, i * 324)) for i, r in enumerate(rows)]; S.save(sys.argv[1]); print("ok")
