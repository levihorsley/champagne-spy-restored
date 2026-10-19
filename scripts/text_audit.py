#!/usr/bin/env python3
"""On-screen text audit: OCR one frame per second of the (deinterlaced, frame-exact) master at true 16:9.
Records every word box (text, confidence, position) so on-screen text can be checked against the subtitles.
Usage: text_audit.py MASTER.mkv WORKDIR OUT.json"""
import sys, os, glob, json, subprocess, concurrent.futures as cf
master, work, out = sys.argv[1:4]
os.makedirs(work, exist_ok=True)
if not glob.glob(f"{work}/*.png"):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", master, "-vf",
                    "select='eq(mod(n\\,25)\\,12)',scale=1024:576:flags=lanczos,setsar=1,format=gray",
                    "-fps_mode", "passthrough", f"{work}/%06d.png"], check=True)
frames = sorted(glob.glob(f"{work}/*.png"))
print("frames to OCR:", len(frames), flush=True)
def ocr(p):
    r = subprocess.run(["tesseract", p, "-", "-l", "eng+deu", "--psm", "11", "tsv"], capture_output=True, text=True)
    words = []
    for line in r.stdout.splitlines()[1:]:
        c = line.split("\t")
        if len(c) == 12 and c[11].strip() and float(c[10]) >= 0:
            words.append(dict(t=c[11].strip(), conf=float(c[10]), x=int(c[6]), y=int(c[7]), w=int(c[8]), h=int(c[9])))
    return os.path.basename(p), words
res = {}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for i, (name, words) in enumerate(ex.map(ocr, frames)):
        res[int(name[:-4]) - 1] = words          # key = second index (frame 25*k+12)
        if i % 500 == 0: print("…", i, flush=True)
json.dump(res, open(out, "w"))
print("done", len(res), flush=True)
