#!/usr/bin/env python3
"""Whitepaper figures: colour-coded change maps per restoration process (vs the disc's own pixels at the same spot).
GOLD = lifted pixel-for-pixel from the neighbouring disc frame (re-pairing; still original pixels)
BLUE = invented by deinterlacing (QTGMC computes the missing lines of a moving frame)
GREEN = the disc's own lines reworked by the QTGMC clean-up of archive line noise
(no colour) = untouched disc pixel."""
import runpy, numpy as np, vapoursynth as vs
from PIL import Image, ImageDraw, ImageFont
W = "~/Movies/ChampagneSpy_work"
g = runpy.run_path(f"{W}/scripts/main_50p.vpy"); o = vs.get_output(0); A = o[0] if isinstance(o, tuple) else o
clip, sel, tff, c = g["clip"], g["sel"], g["tff"], vs.core
GOLD, BLUE, GREEN = (255, 196, 0), (0, 71, 255), (0, 255, 64)
COL = {1: GOLD, 2: BLUE, 3: GREEN}
NAME = {1: "Gold — lifted pixel-for-pixel from the neighbouring disc frame", 2: "Blue — invented by the motion-tracking deinterlacer (QTGMC)", 3: "Green — the disc's own lines reworked by the clean-up pass"}
FB = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 23, index=2); F = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 19, index=0)
Fs = ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", 16, index=0)
def rgb(node, i):
    f = c.resize.Bicubic(node[i], format=vs.RGB24, matrix_in=5).get_frame(0); return np.dstack([np.asarray(f[p]) for p in range(3)])
def change_map(s):
    n = s // 2; out = np.asarray(A.get_frame(s)[0]); disc = np.asarray(clip.get_frame(n)[0]); k = int(sel[s])
    first = (s % 2 == 0); top = first if tff[s] else (not first); kp = 0 if top else 1
    kept = (np.arange(out.shape[0]) % 2 == kp)[:, None]; diff = out != disc; m = np.zeros(out.shape, np.uint8)
    if k in (1, 3, 5, 6): m[diff] = 1
    elif k in (0, 4): m[diff & ~kept] = 2
    elif k in (7, 8): m[diff & ~kept] = 2; m[diff & kept] = 3
    return m
def colour(s):
    enh = rgb(A, s); m = change_map(s); col = enh.copy()
    for v, cc in COL.items(): col[m == v] = cc
    return enh, col, m
def method(s):
    k = int(sel[s]); return {2: "untouched (exact disc picture)", 1: "lifted (re-paired)", 3: "lifted (re-paired)", 5: "lifted (re-paired)", 6: "lifted (re-paired)",
                             0: "half invented by the deinterlacer", 4: "half invented by the deinterlacer", 7: "cleaned up", 8: "cleaned up"}[k]
def step_figure(s, box, title, out, how, key):
    n = s // 2; disc = rgb(clip, n); enh, col, m = colour(s); x0, y0 = box
    Wd, Hw, Zw, Zh, pad = 432, 243, 432, 324, 12
    panels = [("Original DVD", disc, (150, 40, 30)), (f"Enhanced by {how}", enh, (15, 92, 110)), (f"What changed ({key})", col, (40, 40, 40)), ("Final shot", enh, (15, 92, 110))]
    cv = Image.new("RGB", (4 * Wd + 5 * pad, 64 + Hw + pad + Zh + 70), (255, 255, 255)); d = ImageDraw.Draw(cv)
    d.text((pad, 12), title, font=FB, fill=(20, 20, 20))
    for i, (lab, arr, cl) in enumerate(panels):
        x = pad + i * (Wd + pad); d.text((x, 40), f"{i+1}  {lab}", font=F, fill=cl)
        w = Image.fromarray(arr).resize((1024, 576), Image.LANCZOS); ImageDraw.Draw(w).rectangle([x0*1024/720, y0, (x0+160)*1024/720, y0+120], outline=(255, 40, 40), width=6)
        cv.paste(w.resize((Wd, Hw), Image.LANCZOS), (x, 64)); cv.paste(Image.fromarray(arr[y0:y0+120, x0:x0+160]).resize((Zw, Zh), Image.NEAREST), (x, 64 + Hw + pad))
    ly = 64 + Hw + pad + Zh + 12; lx = pad
    for v in (1, 2, 3):
        sh = (m == v).mean()
        if sh == 0: continue
        d.rectangle([lx, ly + 4, lx + 18, ly + 22], fill=COL[v]); t = f"{NAME[v]}: {sh*100:.1f}% of pixels"; d.text((lx + 26, ly), t, font=F, fill=(30, 30, 30)); lx += 26 + int(d.textlength(t, font=F)) + 40
    cv.save(out); print(out, {v: round((m == v).mean() * 100, 1) for v in (1, 2, 3)})
def filmstrip(s0, count, box, title, out):
    x0, y0 = box; cols = 4; Wd, Hw, Zw, Zh, pad = 432, 243, 432, 324, 12
    rows_w = (count + cols - 1) // cols
    H = 64 + rows_w * (Hw + 30 + pad) + 40 + rows_w * (Zh + 30 + pad) + 50
    cv = Image.new("RGB", (cols * Wd + (cols + 1) * pad, H), (255, 255, 255)); d = ImageDraw.Draw(cv)
    d.text((pad, 12), title, font=FB, fill=(20, 20, 20)); y = 56
    maps = [colour(s0 + i) for i in range(count)]
    for i in range(count):
        s = s0 + i; x = pad + (i % cols) * (Wd + pad); yy = y + (i // cols) * (Hw + 30 + pad)
        w = Image.fromarray(maps[i][1]).resize((1024, 576), Image.LANCZOS); ImageDraw.Draw(w).rectangle([x0*1024/720, y0, (x0+160)*1024/720, y0+120], outline=(255, 40, 40), width=6)
        cv.paste(w.resize((Wd, Hw), Image.LANCZOS), (x, yy + 26))
        d.text((x, yy), f"frame {i+1} · +{i*20} ms · {method(s)}", font=Fs, fill=(40, 40, 40))
    y = y + rows_w * (Hw + 30 + pad) + 6; d.text((pad, y), "The same 8 frames, zoomed into the red box", font=F, fill=(15, 92, 110)); y += 34
    for i in range(count):
        s = s0 + i; x = pad + (i % cols) * (Wd + pad); yy = y + (i // cols) * (Zh + 30 + pad)
        cv.paste(Image.fromarray(maps[i][1][y0:y0+120, x0:x0+160]).resize((Zw, Zh), Image.NEAREST), (x, yy + 26))
        d.text((x, yy), f"frame {i+1} · {method(s)}", font=Fs, fill=(40, 40, 40))
    ly = H - 40; lx = pad
    for v in (1, 2, 3):
        d.rectangle([lx, ly + 4, lx + 18, ly + 22], fill=COL[v]); t = NAME[v]; d.text((lx + 26, ly), t, font=Fs, fill=(30, 30, 30)); lx += 26 + int(d.textlength(t, font=Fs)) + 30
    cv.save(out); print(out, cv.size, [method(s0 + i) for i in range(count)])
if __name__ == "__main__":
    E = f"{W}/whitepaper/extra_images"
    step_figure(11138, (30, 150), "Process 1 · Lifted: mis-paired film re-paired from the neighbouring disc frame (Paris street, 3:43)", f"{E}/process_1_lifted_gold.png", "re-pairing", "gold = lifted")
    step_figure(2 * 111850, (470, 228), "Process 2 · Invented: the motion-tracking deinterlacer (QTGMC) fills in what the disc never stored (TV interview, 74:34)", f"{E}/process_2_invented_blue.png", "deinterlacing", "blue = invented")
    step_figure(72836, (280, 200), "Process 3 · Clean-up: the deinterlacer's clean-up pass removes old line noise (archive parade, 24:16)", f"{E}/process_3_cleanup_green.png", "clean-up", "blue + green")
    filmstrip(10931, 8, (330, 200), "All together: 8 consecutive frames (0.16 s) around a scene cut at 3:38 — every process in turn, frame by frame", f"{E}/process_all_filmstrip.png")
