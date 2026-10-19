#!/usr/bin/env python3
"""DVD bitmap subtitles -> SRT.
ffmpeg renders the subtitle stream (with the disc's IFO palette) onto black, keeping one frame per
on-screen change; tesseract reads each frame. A frame with text = cue start; the next change = cue end.
Usage: ocr_subs.py SRC.mkv SUB_INDEX IFO LANG(eng|deu) DURATION_S OUT.srt WORKDIR"""
import sys, os, subprocess, glob, concurrent.futures as cf

src, idx, ifo, lang, dur, out, work = sys.argv[1:8]
os.makedirs(work, exist_ok=True)
for f in glob.glob(f"{work}/*.png"): os.remove(f)
fps = 25
d = float(dur) + 5
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ifo_palette", ifo, "-i", src, "-filter_complex",
    f"color=c=black:s=720x576:r={fps}:d={d}[bg];[bg][0:s:{idx}]overlay=eof_action=pass,"
    "mpdecimate=hi=768:lo=320:frac=0.1,format=gray,negate,scale=iw*2:ih*2:flags=lanczos",
    "-fps_mode", "vfr", "-frame_pts", "1", f"{work}/%010d.png"], check=True)

frames = sorted(glob.glob(f"{work}/*.png"), key=lambda p: int(os.path.basename(p)[:-4]))

def ocr(p):
    r = subprocess.run(["tesseract", p, "-", "-l", lang, "--psm", "6"], capture_output=True, text=True)
    lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    return p, "\n".join(lines), os.path.getsize(p)

with cf.ThreadPoolExecutor(max_workers=6) as ex:
    res = {p: (t, sz) for p, t, sz in ex.map(ocr, frames)}

def ts(s):
    ms = int(round(s * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

cues, suspect = [], 0
for i, p in enumerate(frames):
    text, sz = res[p]
    start = int(os.path.basename(p)[:-4]) / fps
    end = int(os.path.basename(frames[i + 1])[:-4]) / fps if i + 1 < len(frames) else start + 4
    if not text:
        if sz > 20000:            # something is drawn but unreadable -> keep a marker for review
            text = "[unreadable]"; suspect += 1
        else:
            continue              # blank frame = subtitle cleared
    if end - start < 0.2:         # fade/redraw sliver
        continue
    if cues and cues[-1][2] == text and abs(cues[-1][1] - start) < 0.05:
        cues[-1][1] = end         # same text redrawn -> extend
        continue
    cues.append([start, end, text])

with open(out, "w", encoding="utf-8") as f:
    for n, (a, b, t) in enumerate(cues, 1):
        f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{t}\n\n")
print(f"{out}: {len(cues)} cues, {suspect} unreadable, {len(frames)} change frames")
