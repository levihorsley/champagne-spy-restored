#!/usr/bin/env python3
"""Split a title into scenes (scdet) and classify each scene's interlacing (idet).
Usage: classify.py meta.txt out.json [--min-scene 25]
Classes: P = progressive (untouched), T = interlaced top-field-first, B = interlaced bottom-field-first,
         M = mixed (per-frame detect + deinterlace only frames that are interlaced)."""
import sys, json, collections

meta, out = sys.argv[1], sys.argv[2]
MIN = 25  # merge scenes shorter than 1 s into the previous one (idet stats too noisy to judge)

frames = []   # per frame: multi-frame idet verdict
cuts = []     # frame indices where a new scene starts
cur = None
for line in open(meta):
    if line.startswith('frame:'):
        cur = int(line.split()[0].split(':')[1]); frames.append('undetermined')
    elif line.startswith('lavfi.idet.multiple.current_frame='):
        frames[cur] = line.strip().split('=')[1]
    elif line.startswith('lavfi.scd.time=') and cur:
        cuts.append(cur)

n = len(frames)
starts = [0] + [c for c in cuts if c > 0]
# merge too-short scenes
merged = [starts[0]]
for s in starts[1:]:
    if s - merged[-1] >= MIN: merged.append(s)
bounds = list(zip(merged, merged[1:] + [n]))

scenes = []
for a, b in bounds:
    c = collections.Counter(frames[a:b])
    t, bf, p = c['tff'], c['bff'], c['progressive']
    judged = t + bf + p
    il = (t + bf) / judged if judged else 0.0
    if judged < 0.25 * (b - a) or il < 0.10:
        cls = 'P'             # (mostly static / undetermined scenes are safe to leave alone)
    elif il > 0.60 and t >= 4 * bf:
        cls = 'T'
    elif il > 0.60 and bf >= 4 * t:
        cls = 'B'
    else:
        cls = 'M'
    scenes.append(dict(start=a, end=b, cls=cls, tff=t, bff=bf, prog=p, und=c['undetermined']))

json.dump(dict(frames=n, scenes=scenes), open(out, 'w'))

tot = collections.Counter(); cnt = collections.Counter()
for s in scenes:
    tot[s['cls']] += s['end'] - s['start']; cnt[s['cls']] += 1
names = dict(P='progressive (leave untouched)', T='interlaced TFF (deinterlace)', B='interlaced BFF (deinterlace)', M='mixed (per-frame)')
print(f"{n} frames, {len(scenes)} scenes (raw cuts {len(starts)}, merged <{MIN} frames)")
for k in 'PTBM':
    print(f"  {k} {names[k]:32s} scenes={cnt[k]:4d}  frames={tot[k]:6d}  ({tot[k]/n*100:5.1f}%)  {tot[k]/25/60:5.1f} min")
