#!/usr/bin/env python3
"""Full encode, resumable. Film is split at shot boundaries into ~4,000-source-frame chunks (8,000 output frames);
extras are one job each. 5 jobs at a time: vspipe (50 fps master, frame-exact) | x265. Each chunk's output frame count
is checked against the master before it is marked done. Re-run to resume (done chunks are skipped)."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); E = f"{W}/enc"; os.makedirs(E, exist_ok=True)
X265 = ("--preset veryslow --crf 14 --no-sao --output-depth 10 --profile main10 --sar 64:45 --range limited "
        "--colorprim bt470bg --transfer smpte170m --colormatrix bt470bg --no-progress --log-level info").split()
SP = subprocess.run([f"{W}/venv/bin/python", "-c", "import site;print(site.getsitepackages()[0])"], capture_output=True, text=True).stdout.strip()
ENV = dict(os.environ, PYTHONPATH=SP)
shots = json.load(open(f"{W}/scripts/main_shots_interlace.json")); N = 135587
cuts = [0]
for s in shots:
    if s["start"] - cuts[-1] >= 4000: cuts.append(s["start"])
if N - cuts[-1] < 1500: cuts.pop()
cuts.append(N)
jobs = [dict(name=f"main_{i:03d}", script="main_50p.vpy", args=["-a", f"start={a}", "-a", f"end={b}"], frames=2 * (b - a))
        for i, (a, b) in enumerate(zip(cuts[:-1], cuts[1:]))]
jobs += [dict(name="intros", script="extras_50p.vpy", args=["-a", "which=intros"], frames=25282),
         dict(name="x07", script="extras_50p.vpy", args=["-a", "which=07"], frames=23650),
         dict(name="x08", script="extras_50p.vpy", args=["-a", "which=08"], frames=42848)]
json.dump(jobs, open(f"{E}/jobs.json", "w"), indent=1)
def run(j):
    out, log, done = f"{E}/{j['name']}.hevc", f"{E}/{j['name']}.log", f"{E}/{j['name']}.done"
    if os.path.exists(done): return j["name"], "skip"
    t = time.time()
    with open(log, "w") as lf:
        vs = subprocess.Popen(["vspipe", "-c", "y4m", *j["args"], f"{W}/scripts/{j['script']}", "-"], stdout=subprocess.PIPE, stderr=lf, env=ENV)
        x = subprocess.run(["x265", "--input", "-", "--y4m", *X265, "--output", out], stdin=vs.stdout, stderr=lf); vs.stdout.close(); vs.wait()
    txt = open(log).read()
    import re; m = re.search(r"encoded (\d+) frames", txt); got = int(m.group(1)) if m else -1
    ok = x.returncode == 0 and vs.returncode == 0 and got == j["frames"]
    if ok: open(done, "w").write(f"{got} frames {time.time()-t:.0f}s\n")
    return j["name"], f"{'OK' if ok else 'FAILED'} {got}/{j['frames']} frames {time.time()-t:.0f}s"
print(f"{len(jobs)} jobs ({len(cuts)-1} film chunks), {sum(j['frames'] for j in jobs)} frames", flush=True)
ONLY = sys.argv[1] if len(sys.argv) > 1 else "all"   # all | main | extras
import fcntl
LOCK = open(f"{E}/runner_{ONLY}.lock", "w")
try: fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError: print("another runner for", ONLY, "is already running - exiting", flush=True); sys.exit(1)
order = sorted([j for j in jobs if ONLY == "all" or (ONLY == "main") == j["name"].startswith("main_")], key=lambda j: -j["frames"])
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
with ThreadPoolExecutor(WORKERS) as ex:
    for name, res in ex.map(run, order): print(time.strftime("%H:%M"), name, res, flush=True)
bad = [j["name"] for j in order if not os.path.exists(f"{E}/{j['name']}.done")]
print("ALL DONE" if not bad else f"INCOMPLETE: {bad}", flush=True)
