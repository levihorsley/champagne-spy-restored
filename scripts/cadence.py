#!/usr/bin/env python3
"""For every non-progressive shot: is it true video (50 moments/s) or film with shifted field pairing?
in-frame  = difference between frame n's own two fields (blurred, grain-proof)
re-paired = difference between frame n's 2nd field and frame n+1's 1st field
Video: both large on motion. Shifted film: re-paired ~0 while in-frame is large -> re-pair fields = exact film frames.
Usage: cadence.py SOURCE.mkv SHOTS.json META.txt OUT.json"""
import sys, json, numpy as np, vapoursynth as vs
src_p, shots_p, meta_p, out_p = sys.argv[1:5]
c = vs.core; src = c.bs.VideoSource(src_p)
def box(a, k=7):
    p = np.pad(a, ((k, k), (k, k)), mode='edge').cumsum(0).cumsum(1)
    return (p[k:-k, k:-k] - p[:-2*k, k:-k] - p[k:-k, :-2*k] + p[:-2*k, :-2*k])[k//2:k//2+a.shape[0], k//2:k//2+a.shape[1]] / (k*k)
order = {}
cur = None
for l in open(meta_p):
    if l.startswith('frame:'): cur = int(l.split()[0].split(':')[1])
    elif l.startswith('lavfi.idet.multiple.current_frame='): order[cur] = l.strip().split('=')[1]
cache = {}
def fields(n, tff):
    if n not in cache:
        y = np.asarray(src.get_frame(n)[0]).astype(np.float32)
        cache[n] = (box(y[0::2]), box(y[1::2])) if tff else (box(y[1::2]), box(y[0::2]))   # (first, second) in time
        if len(cache) > 64: cache.pop(next(iter(cache)))
    return cache[n]
res = []
for s in json.load(open(shots_p)):
    if s['bucket'].startswith(('progressive', 'static')): continue
    a, b = s['start'], s['end']
    o = [order.get(i) for i in range(a, b)]; tff = o.count('bff') <= o.count('tff')
    step = max(1, (b - a) // 40)
    inf, rep = [], []
    for n in range(a, b - 1, step):
        f1, f2 = fields(n, tff); g1, _ = fields(n + 1, tff)
        inf.append(float(np.mean(np.abs(f1 - f2))[()])); rep.append(float(np.mean(np.abs(f2 - g1))[()]))
    inf, rep = np.array(inf), np.array(rep)
    mv = inf >= 3                                     # frames with real field-to-field change
    ratio = float(np.median(rep[mv] / inf[mv])) if mv.sum() >= 3 else None
    res.append(dict(start=a, end=b, bucket=s['bucket'], tff=tff, moving=int(mv.sum()), samples=len(inf), ratio=ratio))
json.dump(res, open(out_p, 'w'))
print("done", len(res))
