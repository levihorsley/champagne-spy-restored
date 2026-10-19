#!/usr/bin/env python3
"""The decision barcode: every output frame's treatment, as a share per 2-second bin across the film, with a key that
shows each colour and what it means.  Usage: decision_barcode.py OUT.png"""
import sys, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); OUT = sys.argv[1]
code = np.load(f"{W}/scripts/main_fieldmatch.npy")[0]; choice = np.load(f"{W}/scripts/main_qtgmc_choice.npy").astype(bool)
cls = np.where(choice, 3, np.array([2, 1, 0, 1])[code])            # 0 untouched, 1 lifted, 2 calculated, 3 rebuilt
SLATE, GOLD, BLUE, GREEN = "#4F5B63", "#F2B61C", "#1E63E6", "#17B55A"
N = len(cls); FPS = 50; BIN = 2 * FPS; B = int(np.ceil(N / BIN)); sh = np.zeros((4, B))
for b in range(B):
    seg = cls[b * BIN:(b + 1) * BIN]
    for k in range(4): sh[k, b] = (seg == k).mean()
x = np.arange(B) * 2 / 60; pct = [100 * (cls == k).mean() for k in range(4)]
names = [f"Untouched: the disc's own pair ({pct[0]:.1f}%)", f"Lifted: mis-paired film re-paired ({pct[1]:.1f}%)",
         f"Calculated: the missing half ({pct[2]:.1f}%)", f"Rebuilt: line-noise clean-up ({pct[3]:.1f}%)"]
plt.rcParams.update({"font.size": 20, "font.family": "DejaVu Sans"})
fig, ax = plt.subplots(figsize=(21.7, 8.06), dpi=100)
ax.stackplot(x, sh[0] * 100, sh[1] * 100, sh[2] * 100, sh[3] * 100, colors=[SLATE, GOLD, BLUE, GREEN], step="post", linewidth=0)
ax.set_xlim(0, x[-1] + 2 / 60); ax.set_ylim(0, 100); ax.set_yticks([0, 50, 100]); ax.set_yticklabels(["0%", "50%", "100%"])
ax.set_xlabel("Film time (minutes)"); ax.set_xticks(range(0, 91, 10))
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
handles = [Patch(facecolor=c, edgecolor="none") for c in (SLATE, GOLD, BLUE, GREEN)]
fig.legend(handles, names, loc="lower center", ncol=2, frameon=False, handlelength=2.2, handleheight=1.1, columnspacing=3, bbox_to_anchor=(0.5, 0.01))
fig.subplots_adjust(left=0.07, right=0.985, top=0.97, bottom=0.30)
fig.savefig(OUT); print("barcode", OUT, [round(p, 1) for p in pct])
