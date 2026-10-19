#!/usr/bin/env python3
"""x265 calibration on the 10 lossless 50p test scenes (calib/ref_*.y4m).
Variants x CRFs; measures size, speed, VMAF (per frame) and SSIMULACRA2 (per frame). Results -> calib/results.json"""
import subprocess, json, os, time, itertools, sys, numpy as np
from concurrent.futures import ThreadPoolExecutor
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); C = f"{W}/calib"; os.makedirs(f"{C}/enc", exist_ok=True)
COMMON = "--preset veryslow --output-depth 10 --profile main10 --sar 64:45 --range limited --colorprim bt470bg --transfer smpte170m --colormatrix bt470bg --no-progress --log-level error".split()
VARIANTS = {"std": ["--no-sao"], "grain": ["--tune", "grain"]}
CRFS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["14", "16", "18"])]
scenes = [l.split()[0] for l in open(f"{C}/scenes.txt") if l.strip()]
jobs = list(itertools.product(scenes, VARIANTS, CRFS))
def enc(job):
    sc, var, crf = job; base = f"{C}/enc/{sc}_{var}_crf{crf}"
    if os.path.exists(base + ".mkv"): return job, json.load(open(base + ".time.json"))["sec"]
    t = time.time()
    subprocess.run(["x265", "--input", f"{C}/ref_{sc}.y4m", *COMMON, *VARIANTS[var], "--crf", str(crf), "--output", base + ".hevc"], check=True)
    sec = time.time() - t
    subprocess.run(["mkvmerge", "-q", "-o", base + ".mkv", "--default-duration", "0:50fps", base + ".hevc"], check=True)
    os.remove(base + ".hevc"); json.dump({"sec": sec}, open(base + ".time.json", "w")); return job, sec
with ThreadPoolExecutor(5) as ex:
    for (sc, var, crf), sec in ex.map(enc, jobs): print(f"enc {sc} {var} crf{crf}: {sec:.0f}s", flush=True)
def vmaf(job):
    sc, var, crf = job; base = f"{C}/enc/{sc}_{var}_crf{crf}"
    if not os.path.exists(base + ".vmaf.json"):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", base + ".mkv", "-i", f"{C}/ref_{sc}.y4m", "-lavfi",
                        f"[0:v]format=yuv420p10le,setsar=1[d];[1:v]format=yuv420p10le,setsar=1[r];[d][r]libvmaf=log_path={base}.vmaf.json:log_fmt=json:n_threads=3",
                        "-f", "null", "-"], check=True)
    return [f["metrics"]["vmaf"] for f in json.load(open(base + ".vmaf.json"))["frames"]]
with ThreadPoolExecutor(6) as ex: V = dict(zip(jobs, ex.map(vmaf, jobs)))
import vapoursynth as vs
c = vs.core
def rgb(x): return c.resize.Bicubic(x, format=vs.RGBS, matrix_in=5, range_in=0)
res = []
for job in jobs:
    sc, var, crf = job; base = f"{C}/enc/{sc}_{var}_crf{crf}"
    ref = c.bs.VideoSource(f"{C}/ref_{sc}.y4m"); dis = c.bs.VideoSource(base + ".mkv")
    s2 = c.vszip.SSIMULACRA2(rgb(ref), rgb(c.resize.Bicubic(dis, format=vs.YUV420P8, dither_type="none") if False else dis))
    S = [f.props["SSIMULACRA2"] for f in s2.frames(close=True)]
    size = os.path.getsize(base + ".mkv"); v = np.array(V[job]); s = np.array(S)
    r = dict(scene=sc, var=var, crf=crf, kbps=size * 8 / (len(v) / 50) / 1000, sec=json.load(open(base + ".time.json"))["sec"],
             vmaf_mean=v.mean(), vmaf_p1=np.percentile(v, 1), vmaf_min=v.min(), s2_mean=s.mean(), s2_p1=np.percentile(s, 1), s2_min=s.min(),
             worst_frame=int(s.argmin()))
    res.append(r); print(json.dumps({k: (round(x, 2) if isinstance(x, float) else x) for k, x in r.items()}), flush=True)
json.dump(res, open(f"{C}/results.json", "w"), indent=1); print("done", flush=True)
