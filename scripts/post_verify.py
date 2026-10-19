#!/usr/bin/env python3
"""Full re-check of the four finished files (runs automatically after mux_final.py).
1. Video, every frame: the finished file is decoded and compared with the exact 50 fps master it was encoded from
   (re-rendered by the same pipeline) -> VMAF + PSNR per frame (libvmaf). Catches corrupt, missing, shifted or
   swapped frames (PSNR collapses) and reports the worst frames for visual review.
2. Audio: every track checked bit-for-bit against its source (decoded-PCM MD5 for the FLAC, packet MD5s for copied AC-3).
3. Subtitles, chapters, track flags/names/languages, video stream flags, start times, durations.
Report: logs/verify_report.txt (+ per-file VMAF logs in final_build/verify/)."""
import json, os, subprocess, re, numpy as np
W = os.path.expanduser("~/Movies/ChampagneSpy_work"); V = f"{W}/final_build/verify"; os.makedirs(V, exist_ok=True)
OUT = os.path.expanduser("~/Desktop/The Champagne Spy (2007) {tmdb-131748} [576p] [DVDRip] [x265]")
SP = subprocess.run([f"{W}/venv/bin/python", "-c", "import site;print(site.getsitepackages()[0])"], capture_output=True, text=True).stdout.strip()
ENV = dict(os.environ, PYTHONPATH=SP)
FILES = {"film": (f"{OUT}/The Champagne Spy (2007) {tmdb-131748} [576p] [DVDRip] [x265].mkv", "main_50p.vpy", [], 271174),
         "intros": (f"{OUT}/Featurettes/Intros.mkv", "extras_50p.vpy", ["-a", "which=intros"], 25282),
         "oded": (f"{OUT}/Interviews/Oded Gur-Arie.mkv", "extras_50p.vpy", ["-a", "which=07"], 23650),
         "nadav": (f"{OUT}/Interviews/Nadav Schirman (Director).mkv", "extras_50p.vpy", ["-a", "which=08"], 42848)}
rep = []
def say(s): rep.append(s); print(s, flush=True)
def sh(cmd, **kw): return subprocess.run(cmd, capture_output=True, text=True, **kw)
def framemd5(path, sel):
    return [l.split(",")[-1].strip() for l in sh(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-map", sel, "-c", "copy", "-f", "framemd5", "-"]).stdout.splitlines() if not l.startswith("#")]
def pcm_md5(path, sel):
    return sh(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-map", sel, "-f", "md5", "-"]).stdout.strip()
# ---- 1. video vs master, every frame
for key, (f, script, args, n) in FILES.items():
    log = f"{V}/{key}_vmaf.json"
    if not os.path.exists(log):
        vs = subprocess.Popen(["vspipe", "-c", "y4m", *args, f"{W}/scripts/{script}", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=ENV)
        r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", "-", "-i", f, "-lavfi",
            "[0:v]setpts=PTS-STARTPTS,format=yuv420p10le,setsar=1[ref];[1:v:0]setpts=PTS-STARTPTS,format=yuv420p10le,setsar=1[dis];"
            f"[dis][ref]libvmaf=log_path={log}:log_fmt=json:n_threads=16:feature=name=psnr", "-f", "null", "-"], stdin=vs.stdout, capture_output=True, text=True)
        vs.stdout.close(); vs.wait()
    fr = json.load(open(log))["frames"]; vm = np.array([x["metrics"]["vmaf"] for x in fr]); ps = np.array([x["metrics"]["psnr_y"] for x in fr])
    worst = np.argsort(vm)[:12].tolist(); lowpsnr = np.flatnonzero(ps < 30).tolist()
    json.dump(dict(worst_vmaf_frames=worst, low_psnr_frames=lowpsnr[:200]), open(f"{V}/{key}_worst.json", "w"))
    say(f"[video] {key}: compared {len(fr)}/{n} frames {'OK' if len(fr) == n else 'COUNT MISMATCH'} | VMAF mean {vm.mean():.2f}, worst 1% {np.percentile(vm,1):.2f}, min {vm.min():.2f} | "
        f"PSNR-Y mean {ps.mean():.2f} dB, min {ps.min():.2f} dB | frames below 30 dB: {len(lowpsnr)}")
# ---- 2. audio bit-exactness
film, intros, oded, nadav = (FILES[k][0] for k in ("film", "intros", "oded", "nadav"))
a = pcm_md5(film, "0:a:0"); b = pcm_md5(f"{W}/audio/german_corrected_seamless.flac", "0:a:0")
say(f"[audio] film German FLAC decodes bit-identical to the prepared track: {a == b} ({a[-12:]})")
for label, f, sel, src, ssel in (("film Hebrew AC-3", film, "0:a:1", f"{W}/main_source.mkv", "0:a:1"),
                                 ("Intros AC-3", intros, "0:a:0", f"{W}/final_build/intros_audio.mka", "0:a:0"),
                                 ("Oded English AC-3", oded, "0:a:0", f"{W}/x07_source.mkv", "0:a:0"),
                                 ("Nadav English AC-3", nadav, "0:a:0", f"{W}/x08_source.mkv", "0:a:0")):
    x, y = framemd5(f, sel), framemd5(src, ssel)
    say(f"[audio] {label}: {len(x)} packets, bit-identical to source: {x == y}" + ("" if x == y else f" (source {len(y)} packets)"))
# ---- 3. streams, flags, subtitles, chapters
for key, (f, *_ ) in FILES.items():
    j = json.loads(sh(["mkvmerge", "-J", f]).stdout)
    tr = [(t["type"], t["properties"].get("language"), t["properties"].get("track_name"), t["properties"].get("default_track"), t["properties"].get("forced_track"),
           t["properties"].get("display_dimensions") or t["properties"].get("audio_channels")) for t in j["tracks"]]
    ch = sum(len(e.get("num_entries", 0) and [1]) for e in j.get("chapters", [])) if j.get("chapters") else 0
    nch = j["chapters"][0]["num_entries"] if j.get("chapters") else 0
    st = sh(["ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,start_time,duration", "-of", "csv=p=0", f]).stdout.strip().replace("\n", " | ")
    vinfo = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,profile,level,pix_fmt,width,height,sample_aspect_ratio,display_aspect_ratio,r_frame_rate,color_range,color_space,color_primaries,color_transfer", "-of", "default=nw=1", f]).stdout.split()
    say(f"[file] {key}: {os.path.getsize(f)/1e9:.2f} GB | chapters {nch} | tracks (type, lang, name, default, forced, dims/ch): {tr}")
    say(f"       video: {' '.join(vinfo)}"); say(f"       start/duration: {st}")
def srt_cues(text):
    out = []
    for b in text.strip().replace("\r", "").split("\n\n"):
        l = b.split("\n")
        if len(l) >= 3 and "-->" in l[1]: out.append((l[1].strip(), "\n".join(l[2:]).strip()))
    return out
for label, f, sel, src in (("English", film, "0:s:0", f"{W}/final_build/english_full.srt"), ("German (Forced)", film, "0:s:1", f"{W}/main_ger_forced.srt"),
                           ("Oded German", oded, "0:s:0", f"{W}/x07_ger.srt"), ("Nadav German", nadav, "0:s:0", f"{W}/x08_ger.srt")):
    got = srt_cues(sh(["ffmpeg", "-nostdin", "-v", "error", "-i", f, "-map", sel, "-f", "srt", "-"]).stdout); want = srt_cues(open(src, encoding="utf-8").read())
    same_text = [g[1] for g in got] == [w[1] for w in want]; same_time = [g[0] for g in got] == [w[0] for w in want]
    say(f"[subs] {label}: {len(got)} cues (source {len(want)}), text identical {same_text}, times identical {same_time}")
open(f"{W}/logs/verify_report.txt", "w").write("\n".join(rep) + "\n"); print("VERIFY DONE", flush=True)
