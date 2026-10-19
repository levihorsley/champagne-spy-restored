#!/usr/bin/env python3
"""Intros audio: each piece's original AC-3 frames copied bit-for-bit and pinned to the exact moment its picture
starts in Intros.mkv (piece start + the disc's own audio/video offset); silence (AC-3, 2.0, 192 kb/s) where the disc
has none: under the copyright card and after the logo's sound ends. Output: final_build/intros_audio.mka
Piece starts (50p video, from frame counts): 01 0.00 | 02 16.00 | 03 40.04 | 04 165.80 | 05 277.12 | 06 398.32 (s)"""
import subprocess, os, json
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); B = f"{W}/final_build"; T = f"{B}/ia"; os.makedirs(T, exist_ok=True)
frames = {n: json.load(open(f"{W}/scripts/x{n}_scenes.json"))["frames"] for n in ("01","02","03","04","05","06")}
start, t = {}, 0.0
for n in ("01","02","03","04","05","06"): start[n] = t; t += frames[n] / 25
total = t
def probe(p, k): return [x.strip(",") for x in subprocess.run(["ffprobe","-v","error","-show_entries",f"stream={k}","-of","csv=p=0",p],capture_output=True,text=True).stdout.split()]
parts = []   # (raw ac3 path, first-frame time in seconds)
# disc audio/video offset per piece: audio_start - video_start
for n in ("02","03","04","05","06"):
    src = f"{W}/x{n}_source.mkv"; v0 = float(probe(src, "start_time")[0]); a0 = float(probe(src, "start_time")[1])
    out = f"{T}/x{n}.ac3"; subprocess.run(["ffmpeg","-nostdin","-v","error","-i",src,"-map","0:a:0","-c","copy","-y",out], check=True)
    parts.append((out, start[n] + (a0 - v0)))
def silence(path, seconds):
    k = int(seconds / 0.032 + 1e-6)
    if k <= 0: return None
    subprocess.run(["ffmpeg","-nostdin","-v","error","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{k*0.032:.3f}","-c:a","ac3","-b:a","192k","-y",path], check=True); return path
# build the full frame timeline: silence before first piece and in every gap >= 32 ms
seq, cur = [], 0.0
for i, (p, t0) in enumerate(parts):
    gap = t0 - cur
    if gap >= 0.032:
        s = silence(f"{T}/sil{i}.ac3", gap); seq.append((s, cur))
    seq.append((p, t0))
    nfr = int(subprocess.run(["ffprobe","-v","error","-count_packets","-show_entries","stream=nb_read_packets","-of","csv=p=0",p],capture_output=True,text=True).stdout)
    cur = t0 + nfr * 0.032
# tail silence to the end of the video
if total - cur >= 0.032: seq.append((silence(f"{T}/siltail.ac3", total - cur), cur))
# concatenate raw frames + v2 timestamp file (one line per AC-3 frame, ms)
raw = f"{T}/all.ac3"; ts = f"{T}/timestamps.txt"; lines = ["# timestamp format v2"]
with open(raw, "wb") as o:
    for p, t0 in seq:
        nfr = int(subprocess.run(["ffprobe","-v","error","-count_packets","-show_entries","stream=nb_read_packets","-of","csv=p=0",p],capture_output=True,text=True).stdout)
        o.write(open(p, "rb").read()); lines += [f"{(t0 + k*0.032)*1000:.3f}" for k in range(nfr)]
open(ts, "w").write("\n".join(lines) + "\n")
subprocess.run(["mkvmerge","-q","-o",f"{B}/intros_audio.mka","--disable-lacing","--timestamps",f"0:{ts}","--language","0:de","--track-name","0:German",raw], check=True)
print("pieces:", [(os.path.basename(p), round(t0,3)) for p,t0 in seq]); print("video length", total, "audio frames", len(lines)-1)
