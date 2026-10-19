#!/usr/bin/env python3
"""Provenance gallery for the README.  Usage: provenance_gallery.py OUTDIR
For each chosen output frame: (1) the DVD frame as stored, (2) every line coloured by where it came from, in the decision
barcode's colours, (3) the finished frame; full frame on top, a zoom below; pixel counts per class in the legend.  The
finished frame is rendered live through main_50p.vpy (the pipeline that fed the encoder) and every line's origin is checked
bit-exact against the disc: own lines must equal the source frame, lifted lines the neighbouring source frame, calculated
and rebuilt lines neither.  Also writes cars_before_after.png (the Paris street frame, as stored / repaired, stacked large)
and one_shot_24_frames.png (24 consecutive output frames of one shot, each tinted by its treatment), and prints the
film-wide pixel totals per class."""
import sys, os, numpy as np, vapoursynth as vs
from PIL import Image, ImageDraw, ImageFont
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, f"{W}/scripts"); from fm_common import load
c = vs.core; S = c.bs.VideoSource(f"{W}/main_source.mkv")
G = {"__name__": "provenance_gallery"}; exec(open(f"{W}/scripts/main_50p.vpy").read(), G); E = G["out"]     # the live 50p pipeline
code = np.load(f"{W}/scripts/main_fieldmatch.npy")[0]; choice = np.load(f"{W}/scripts/main_qtgmc_choice.npy").astype(bool); tff = load()["tff"]
SLATE, GOLD, BLUE, GREEN = (0x4F, 0x5B, 0x63), (0xF2, 0xB6, 0x1C), (0x1E, 0x63, 0xE6), (0x17, 0xB5, 0x5A)   # the barcode's colours
OWN, NEIGH, CALC, REBUILT = 0, 1, 2, 3; COL = {OWN: SLATE, NEIGH: GOLD, CALC: BLUE, REBUILT: GREEN}
CNAME = {OWN: "slate", NEIGH: "gold", CALC: "blue", REBUILT: "green"}
LEG = {OWN: "Untouched: this disc frame's own line", NEIGH: "Lifted: from the neighbouring disc frame, bit-exact",
       CALC: "Calculated: the half the disc never had", REBUILT: "Rebuilt: the shot was cleaned of transfer line noise"}
DECISION = {OWN: "Decision: the disc's own pair. Both halves of this instant were on the disc together, so the frame is used exactly as stored.",
            NEIGH: "Decision: lifted. The disc stored this instant's two halves in different frames; the missing half was lifted back from the neighbouring disc frame, bit-exact.",
            CALC: "Decision: calculated. The disc never recorded the other half of this instant, so those lines were calculated; the disc's own lines are kept bit-exact.",
            REBUILT: "Decision: rebuilt. Old transfer line noise was printed into this shot; it was rebuilt clean, one of 116 such shots."}
F = lambda size, bold: ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size, index=1 if bold else 0)
F_T, F_D, F_H, F_L = F(30, True), F(20, False), F(22, True), F(19, False)
PW, PH, GAP = 580, 326, 30; CW = 3 * PW + 2 * GAP; CROP_W, CROP_H = 90, 72          # 90x72 disc pixels display as 16:9; zoom 4.5x
PPL = 720; PPF = 720 * 576                                                              # pixels per line, per frame
def luma(clip, i): return np.asarray(clip.get_frame(i)[0])
def rgb(clip, i, w, h):
    f = c.resize.Spline36(clip[i], w, h, format=vs.RGB24, matrix_in=5).get_frame(0); return np.dstack([np.asarray(f[p]) for p in range(3)])
def rgb_zoom(clip, i, box, w, h):
    x, y, cw, ch = box
    f = c.resize.Bicubic(c.std.Crop(clip[i], left=x, right=720 - x - cw, top=y, bottom=576 - y - ch), w, h, format=vs.RGB24, matrix_in=5).get_frame(0)
    return np.dstack([np.asarray(f[p]) for p in range(3)])
def frame_class(s): return REBUILT if choice[s] else {0: CALC, 1: NEIGH, 2: OWN, 3: NEIGH}[int(code[s])]
def provenance(slot):
    """class per line (576,) from the decision and the pipeline's field assignment (top field = even lines)."""
    n = slot // 2; t = bool(tff[n]); k = int(code[slot]); even = np.arange(576) % 2 == 0; cls = np.full(576, OWN, np.int8)
    if choice[slot]: cls[:] = REBUILT
    elif k == 0:                                           # QTGMC: slot 2n is the first field in time (top for TFF), 2n+1 the other
        kept_top = t if slot % 2 == 0 else not t; cls[~even if kept_top else even] = CALC
    elif k == 1: cls[~even if t else even] = NEIGH         # TFF: own top + previous bottom;  BFF: own bottom + previous top
    elif k == 3: cls[even if t else ~even] = NEIGH         # TFF: own bottom + next top;      BFF: own top + next bottom
    return cls
def verify(slot, cls):
    n = slot // 2; M = luma(E, slot); Yn = luma(S, n); k = int(code[slot])
    Yq = luma(S, max(n - 1, 0) if k == 1 else min(n + 1, S.num_frames - 1))
    own, nb = (M == Yn).all(1), (M == Yq).all(1); r = {}
    for cl, arr, want in ((OWN, own, True), (NEIGH, nb, True), (CALC, own, False), (REBUILT, own, False)):
        m = cls == cl
        if m.any(): r[cl] = (int((arr[m] == want).sum()), int(m.sum()))
    return r
def energy(y, want):
    y = y.astype(np.float32); d = np.zeros_like(y)
    if want == REBUILT: d[1:-1] = np.maximum(np.abs(y[1:-1] - y[2:]) - np.abs(y[:-2] - y[2:]), 0)
    elif want == OWN:   d[1:-1, 1:-1] = np.abs(y[1:-1, 1:-1] - y[1:-1, :-2]) + np.abs(y[1:-1, 1:-1] - y[:-2, 1:-1])
    else:               d[1:-1] = np.abs(y[1:-1] - 0.5 * (y[:-2] + y[2:]))
    return d
def boxsum(d, cw, ch):
    p = np.pad(d.cumsum(0).cumsum(1), ((1, 0), (1, 0))); return p[ch:, cw:] - p[:-ch, cw:] - p[ch:, :-cw] + p[:-ch, :-cw]   # window sums, top-left indexed
def pick_box(y, yfin, want, cw=CROP_W, ch=CROP_H):
    """Where to zoom: the window with the most defect energy on the disc frame, weighted by how much detail the finished
    frame has there (so the zoom lands on a car or a face, not on a blank wall that merely combs)."""
    e = boxsum(energy(y, want), cw, ch); det = boxsum(energy(yfin, OWN), cw, ch)
    score = e * (det / (det.mean() + 1e-6)) if want != OWN else det
    score[:16] = 0; score[-16:] = 0; score[:, :16] = 0; score[:, -16:] = 0
    cy, cx = np.unravel_index(score.argmax(), score.shape); return (int(cx) & ~1, int(cy) & ~1, cw, ch)
def pick_slot(t0, t1, want):
    best = None; cache = {}
    for s in range(int(t0 * 50), int(t1 * 50)):
        if frame_class(s) != want: continue
        n = s // 2
        if n not in cache: cache[n] = float(energy(luma(S, n), want).mean())
        if best is None or cache[n] > best[0]: best = (cache[n], s)
    return best[1] if best else None
def tstr(slot): t = slot / 50; return f"{int(t // 60)}:{t % 60:05.2f}"
def label(d, text, xy, font, fill, bg=(0, 0, 0, 170)):
    x, y = xy; tw = d.textlength(text, font=font); d.rectangle([x - 8, y - 4, x + tw + 8, y + font.size + 6], fill=bg); d.text((x, y), text, font=font, fill=fill)
def colour_native(slot, cls):
    g = luma(E, slot).astype(np.float32); img = np.repeat(g[:, :, None], 3, axis=2)
    for cl in (OWN, NEIGH, CALC, REBUILT):
        m = cls == cl
        if not m.any(): continue
        a = 0.34 if cl == OWN else 0.80; img[m] = (1 - a) * img[m] + a * np.array(COL[cl], np.float32)
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))
def pixel_line(cls):
    parts = []
    for cl, word in ((CALC, "calculated"), (REBUILT, "rebuilt"), (NEIGH, "lifted, bit-exact"), (OWN, "untouched")):
        m = int((cls == cl).sum())
        if m: parts.append(f"{m * PPL:,} {word}")
    return f"Pixels in this frame ({PPF:,}):  " + "  ·  ".join(parts)

TOP = 96
def figure(slot, desc, path):
    n = slot // 2; cls = provenance(slot); cl = frame_class(slot); v = verify(slot, cls); box = pick_box(luma(S, n), luma(E, slot), cl)
    x, y, cw, ch = box; cv = Image.new("RGB", (CW, TOP + 36 + PH + 14 + 36 + PH + 14 + 100), (12, 12, 14)); d = ImageDraw.Draw(cv, "RGBA")
    d.text((0, 6), f"{tstr(slot)}  ·  {desc}", font=F_T, fill=GOLD); d.text((0, 44), DECISION[cl], font=F_D, fill=(205, 205, 205))
    d.text((0, 68), pixel_line(cls), font=F_D, fill=COL[cl] if cl != OWN else (170, 180, 186))
    y1 = TOP + 36; y2 = y1 + PH + 14 + 36
    heads = ("1 · As stored on the DVD", "2 · Every line coloured by where it came from", "3 · The finished frame")
    cimg = colour_native(slot, cls)
    full = [Image.fromarray(rgb(S, n, PW, PH)), cimg.resize((PW, PH), Image.BOX), Image.fromarray(rgb(E, slot, PW, PH))]
    zoom = [Image.fromarray(rgb_zoom(S, n, box, PW, PH)), cimg.crop((x, y, x + cw, y + ch)).resize((PW, PH), Image.NEAREST), Image.fromarray(rgb_zoom(E, slot, box, PW, PH))]
    for i, h in enumerate(heads):
        px = i * (PW + GAP); d.text((px, y1 - 30), h, font=F_H, fill=(235, 235, 235)); d.text((px, y2 - 30), "Zoomed 4.5×  ·  " + h.split("· ")[1], font=F_H, fill=(235, 235, 235))
        cv.paste(full[i], (px, y1)); cv.paste(zoom[i], (px, y2))
        sx, sy = PW / 720, PH / 576; d.rectangle([px + x * sx, y1 + y * sy, px + (x + cw) * sx, y1 + (y + ch) * sy], outline=(255, 60, 60), width=3)
    ly = y2 + PH + 14 + 10; lx = 0
    for cl2 in (OWN, NEIGH, CALC, REBUILT):
        m = int((cls == cl2).sum()); dim = m == 0
        d.rectangle([lx, ly + 2, lx + 26, ly + 22], fill=COL[cl2] if not dim else (60, 60, 64))
        chk = ""
        if not dim and cl2 in v: ok, tot = v[cl2]; chk = f"  ({tot} lines, {tot * PPL:,} px; {ok} of {tot} {'bit-exact' if cl2 in (OWN, NEIGH) else 'changed'})"
        txt = LEG[cl2] + (chk if not dim else "  (none in this frame)"); d.text((lx + 36, ly), txt, font=F_L, fill=(225, 225, 225) if not dim else (120, 120, 124)); ly += 24
        if cl2 == NEIGH: ly = y2 + PH + 14 + 10; lx = CW // 2
    cv.save(path, optimize=True); print(f"{os.path.basename(path)}: slot {slot} disc {n} {tstr(slot)} class {CNAME[cl]} tff={bool(tff[n])} code={int(code[slot])} box={box} verify={v}", flush=True)

ENTRIES = [("archive television, a man speaking", CALC, (43.5, 46.0), None),
           ("archive film, the Paris street", NEIGH, None, 11244),
           ("the Paris street, two output frames later", OWN, (224.9, 225.08), None),
           ("the Eiffel Tower, a few frames on", CALC, (225.1, 228.0), None),
           ("archive film", NEIGH, (640.0, 690.0), None),
           ("archive transfer", REBUILT, (1220.0, 1260.0), None),
           ("archive transfer, a ribbed shirt", REBUILT, (1424.5, 1428.0), None),
           ("archive transfer, a parade salute", REBUILT, (1463.8, 1466.0), None),
           ("archive television", CALC, (2690.0, 2720.0), None),
           ("archive transfer", REBUILT, (3020.0, 3060.0), None),
           ("archive television, a motorcade", REBUILT, (3181.0, 3185.0), None),
           ("archive television, a hand", CALC, (4477.0, 4480.0), None),
           ("the end credits, rolling", NEIGH, (5310.0, 5420.0), None)]
k = 0
for desc, want, rng, fixed in ENTRIES:
    slot = fixed if fixed is not None else pick_slot(rng[0], rng[1], want)
    if slot is None: print("NO FRAME for", desc, want, rng, flush=True); continue
    k += 1; figure(slot, desc, f"{OUT}/frame_{k:02d}.png")

# ---- one shot, 24 consecutive output frames, each tinted by its treatment (the Paris street, from its first frame)
n0 = 5564; s0 = 2 * n0; TW_, TH_, GX, GY = 218, 123, 8, 44; cols = 8; rows = 3
cv = Image.new("RGB", (cols * TW_ + (cols - 1) * GX, 96 + rows * (TH_ + GY) + 44), (12, 12, 14)); d = ImageDraw.Draw(cv)
d.text((0, 6), "One shot, 24 consecutive output frames (0.48 s): the treatment changes frame by frame", font=F_T, fill=GOLD)
cnt = {OWN: 0, NEIGH: 0, CALC: 0, REBUILT: 0}
for i in range(cols * rows):
    s = s0 + i; cls = provenance(s); cl = frame_class(s); cnt[cl] += 1
    im = colour_native(s, cls).resize((TW_, TH_), Image.BOX); x = (i % cols) * (TW_ + GX); y = 96 + (i // cols) * (TH_ + GY)
    cv.paste(im, (x, y)); d.rectangle([x, y + TH_ + 4, x + TW_, y + TH_ + 10], fill=COL[cl])
    d.text((x, y + TH_ + 14), f"frame {i + 1}", font=F_L, fill=(225, 225, 225))
shot_n = 5627 - 5564; tot = {cl: 0 for cl in cnt}
for s in range(s0, s0 + 2 * shot_n): tot[frame_class(s)] += 1
d.text((0, 46), f"The Paris street, 3:42-3:45, {2 * shot_n} frames: {tot[CALC]} calculated, {tot[NEIGH]} lifted, {tot[OWN]} untouched.  "
                f"Pixels in the shot: {2 * shot_n * PPF:,}; {tot[CALC] * PPF // 2:,} calculated, {tot[NEIGH] * PPF // 2:,} lifted, the rest untouched.", font=F_D, fill=(205, 205, 205))
ky = 96 + rows * (TH_ + GY) + 8; kx = 0
for cl in (OWN, NEIGH, CALC, REBUILT):                      # the key, in the strip itself
    d.rectangle([kx, ky + 2, kx + 26, ky + 22], fill=COL[cl]); d.text((kx + 36, ky), LEG[cl], font=F_L, fill=(225, 225, 225)); kx += 36 + int(d.textlength(LEG[cl], font=F_L)) + 48
cv.save(f"{OUT}/one_shot_24_frames.png", optimize=True); print("one_shot_24_frames.png:", cnt, "shot totals", tot, flush=True)

# ---- the key on its own (for the README text)
cv = Image.new("RGB", (CW, 76), (12, 12, 14)); d = ImageDraw.Draw(cv); kx = 0; ky = 8
for cl in (OWN, NEIGH, CALC, REBUILT):
    if cl == CALC: kx = 0; ky = 42
    d.rectangle([kx, ky + 2, kx + 26, ky + 22], fill=COL[cl]); d.text((kx + 36, ky), LEG[cl], font=F_L, fill=(225, 225, 225)); kx = CW // 2
cv.save(f"{OUT}/key.png", optimize=True); print("key.png", flush=True)

# ---- the hero pair: the Paris street frame (slot 11244), as stored / repaired, stacked large
n0, n1 = 5564, 5627; acc = np.zeros((576, 720), np.float32)
for n in range(n0, n1, 2): acc += energy(luma(S, n), NEIGH)
kk = 24; p = np.pad(acc, ((kk, kk), (kk, kk)), mode="edge").cumsum(0).cumsum(1); bx = (p[2*kk:, 2*kk:] - p[:-2*kk, 2*kk:] - p[2*kk:, :-2*kk] + p[:-2*kk, :-2*kk])[:576, :720]
cw, ch = 300, 240; bx[:ch//2+8] = 0; bx[-ch//2-8:] = 0; bx[:, :cw//2+8] = 0; bx[:, -cw//2-8:] = 0
cy, cx = np.unravel_index(bx.argmax(), bx.shape); hbox = (int(cx - cw // 2) & ~1, int(cy - ch // 2) & ~1, cw, ch)
slot = 11244; HW, HH = 1600, 900; cv = Image.new("RGB", (HW, 2 * HH + 8), (12, 12, 14))
cv.paste(Image.fromarray(rgb_zoom(S, slot // 2, hbox, HW, HH)), (0, 0)); cv.paste(Image.fromarray(rgb_zoom(E, slot, hbox, HW, HH)), (0, HH + 8))
d = ImageDraw.Draw(cv, "RGBA"); FB = F(40, True)
label(d, "ORIGINAL DVD  ·  the frame as stored, 3:44", (28, 24), FB, (255, 120, 110)); label(d, "RESTORED  ·  the same instant, its halves re-paired. No pixel invented.", (28, HH + 8 + 24), FB, (120, 235, 240))
cv.save(f"{OUT}/cars_before_after.png", optimize=True); print("cars_before_after.png: slot", slot, "box", hbox, "verify", verify(slot, provenance(slot)), flush=True)

# ---- film-wide pixel totals per class (every output frame)
N = len(code); cls_all = np.where(choice, REBUILT, np.array([CALC, NEIGH, OWN, NEIGH])[code]); half = PPF // 2
pix = {OWN: int((cls_all == OWN).sum()) * PPF + int(((cls_all == CALC) | (cls_all == NEIGH)).sum()) * half,
       NEIGH: int((cls_all == NEIGH).sum()) * half, CALC: int((cls_all == CALC).sum()) * half, REBUILT: int((cls_all == REBUILT).sum()) * PPF}
T = N * PPF; print(f"FILM: {N:,} frames, {T:,} pixels.  untouched {pix[OWN]:,} ({100*pix[OWN]/T:.1f}%)  lifted {pix[NEIGH]:,} ({100*pix[NEIGH]/T:.1f}%)  "
                   f"calculated {pix[CALC]:,} ({100*pix[CALC]/T:.1f}%)  rebuilt {pix[REBUILT]:,} ({100*pix[REBUILT]/T:.1f}%)  altered {pix[CALC]+pix[REBUILT]:,} ({100*(pix[CALC]+pix[REBUILT])/T:.1f}%)", flush=True)
