#!/usr/bin/env python3
"""Assemble the four finished files on the Desktop, then verify. Run after encode_run.py reports ALL DONE.
Sync: every master starts at source time 0.04 s, so video (and the German FLAC, which starts at the Hebrew track's
first sample) get +40 ms; tracks copied from the source keep their own 0.04 s start; subtitle times are source timeline."""
import json, os, subprocess, re
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); E = f"{W}/enc"; B = f"{W}/final_build"; os.makedirs(B, exist_ok=True)
OUT = os.path.expanduser("~/Desktop/The Champagne Spy (2007) {tmdb-131748} [576p] [DVDRip] [x265]")
for d in ("", "/Featurettes", "/Interviews"): os.makedirs(OUT + d, exist_ok=True)
COLOUR = ["--colour-matrix-coefficients", "0:5", "--colour-transfer-characteristics", "0:6", "--colour-primaries", "0:5", "--colour-range", "0:1"]
def run(cmd): r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode in (0, 1), r.stdout + r.stderr; return r.stdout
def ts(x):
    h, m, r = x.split(":"); s, ms = r.split(","); return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
def fmt(t):
    ms = round(t*1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000); return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
def srt(p):
    for b in open(p, encoding="utf-8").read().strip().split("\n\n"):
        l = b.split("\n"); a, c = l[1].split(" --> "); yield ts(a), ts(c), "\n".join(l[2:])
# 1. English subtitles = dialogue (788) + translations of German on-screen text (15)
cues = sorted(list(srt(f"{W}/main_eng.srt")) + list(srt(f"{W}/subs_added_english.srt")), key=lambda x: (x[0], x[1]))
open(f"{B}/english_full.srt", "w", encoding="utf-8").write("\n".join(f"{i}\n{fmt(a)} --> {fmt(c)}\n{t}\n" for i, (a, c, t) in enumerate(cues, 1)))
# 2. film video: chunks in order -> one stream
jobs = json.load(open(f"{E}/jobs.json")); chunks = [j for j in jobs if j["name"].startswith("main_")]
with open(f"{B}/main_video.hevc", "wb") as o:
    for j in chunks: o.write(open(f"{E}/{j['name']}.hevc", "rb").read())
film = f"{OUT}/The Champagne Spy (2007) {tmdb-131748} [576p] [DVDRip] [x265].mkv"
run(["mkvmerge", "-o", film, "--title", "The Champagne Spy", "--chapters", f"{W}/scripts/main_chapters_named.txt",
     "--default-duration", "0:50fps", "--sync", "0:40", *COLOUR, f"{B}/main_video.hevc",
     "--language", "0:de", "--track-name", "0:German", "--default-track-flag", "0:yes", "--sync", "0:40", f"{W}/audio/german_corrected_seamless.flac",
     "--no-video", "--no-subtitles", "--no-chapters", "--audio-tracks", "2", "--language", "2:he", "--track-name", "2:Hebrew (Original)", "--default-track-flag", "2:no", f"{W}/main_source.mkv",
     "--language", "0:en", "--track-name", "0:English", "--default-track-flag", "0:yes", f"{B}/english_full.srt",
     "--language", "0:de", "--track-name", "0:German (Forced)", "--forced-display-flag", "0:yes", "--default-track-flag", "0:no", f"{W}/main_ger_forced.srt"])
# 3. extras
intros = f"{OUT}/Featurettes/Intros.mkv"
run(["mkvmerge", "-o", intros, "--title", "Intros", "--chapters", f"{W}/scripts/intro_chapters.txt",
     "--default-duration", "0:50fps", *COLOUR, f"{E}/intros.hevc",
     "--disable-lacing", "--language", "0:de", "--track-name", "0:German", f"{B}/intros_audio.mka"])
oded = f"{OUT}/Interviews/Oded Gur-Arie.mkv"
run(["mkvmerge", "-o", oded, "--title", "Oded Gur-Arie", "--default-duration", "0:50fps", "--sync", "0:40", *COLOUR, f"{E}/x07.hevc",
     "--no-video", "--no-subtitles", "--no-chapters", "--audio-tracks", "1", "--language", "1:en", "--track-name", "1:English", "--default-track-flag", "1:yes", f"{W}/x07_source.mkv",
     "--language", "0:de", "--track-name", "0:German", "--default-track-flag", "0:no", f"{W}/x07_ger.srt"])
nadav = f"{OUT}/Interviews/Nadav Schirman (Director).mkv"
run(["mkvmerge", "-o", nadav, "--title", "Nadav Schirman (Director)", "--chapters", f"{W}/scripts/x08_chapters.txt",
     "--default-duration", "0:50fps", "--sync", "0:40", *COLOUR, f"{E}/x08.hevc",
     "--no-video", "--no-subtitles", "--no-chapters", "--audio-tracks", "1", "--language", "1:en", "--track-name", "1:English", "--default-track-flag", "1:yes", f"{W}/x08_source.mkv",
     "--language", "0:de", "--track-name", "0:German", "--default-track-flag", "0:no", f"{W}/x08_ger.srt"])
# 4. verify: frame counts, start times, full decode
want = {film: 271174, intros: 25282, oded: 23650, nadav: 42848}
for f, n in want.items():
    pk = int(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", f]).strip())
    st = run(["ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,start_time:stream_tags=language,title", "-of", "csv=p=0", f]).strip().replace("\n", " | ")
    dec = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", f, "-map", "0:v", "-map", "0:a", "-f", "null", "-"], capture_output=True, text=True).stderr.strip()
    print(f"{os.path.basename(f)}: video frames {pk}/{n} {'OK' if pk == n else 'MISMATCH'} | decode errors: {dec[:200] or 'none'}\n   {st}", flush=True)
