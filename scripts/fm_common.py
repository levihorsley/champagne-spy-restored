"""Shared loader for per-field (slot) matching data. Slot 2n = first field of frame n in time order, 2n+1 = second.
Candidates: TFF  slot 2n (T_n): prev=B_{n-1} (X[n-1]) | in=B_n (C[n]);  slot 2n+1 (B_n): in=T_n (C[n]) | next=T_{n+1} (X[n])
            BFF  slot 2n (B_n): prev=T_{n-1} (Y[n-1]) | in=T_n (C[n]);  slot 2n+1 (T_n): in=B_n (C[n]) | next=B_{n+1} (Y[n])
load()      -> main film (shot buckets + cadence field order)
load('x07') -> an extra (scene classes from xNN_scenes.json: P progressive, T/B interlaced TFF/BFF, M mixed)"""
import numpy as np, csv, json, os
D = os.path.dirname(os.path.abspath(__file__))
BUCKET = {"P": "progressive (both detectors)", "T": "interlaced (both detectors)", "B": "interlaced (both detectors)", "M": "mixed within shot"}
def load(prefix="main"):
    X, Y = np.load(f"{D}/{prefix}_crossweave.npy")
    C = np.array([int(r["blockmax"]) for r in csv.DictReader(open(f"{D}/{prefix}_combblocks.csv"))])
    N = len(C); tff = np.ones(N, bool); bucket = np.empty(N, object)
    if prefix == "main":
        shots = json.load(open(f"{D}/main_shots_interlace.json")); cad = {s["start"]: s for s in json.load(open(f"{D}/main_cadence.json"))}
        for s in shots:
            cs = cad.get(s["start"])
            if cs is not None and cs.get("tff") is False: tff[s["start"]:s["end"]] = False
            bucket[s["start"]:s["end"]] = s["bucket"]
    else:
        shots = json.load(open(f"{D}/{prefix}_scenes.json"))["scenes"]
        for s in shots:
            tff[s["start"]:s["end"]] = s["cls"] != "B"; bucket[s["start"]:s["end"]] = BUCKET[s["cls"]]
    Xp, Yp = np.r_[9999, X[:-1]], np.r_[9999, Y[:-1]]
    prev = np.where(tff, Xp, Yp); nxt = np.where(tff, X, Y)
    return dict(C=C, X=X, Y=Y, prev=prev, nxt=nxt, tff=tff, bucket=bucket, shots=shots, N=N)
