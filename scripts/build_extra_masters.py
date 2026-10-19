#!/usr/bin/env python3
"""Per-scene deinterlaced lossless masters for the extras (same method as the main film).
P = untouched, T = bwdif top-field-first, B = bwdif bottom-field-first, M = per-frame detect.
4:3 title sets are pillarboxed into the 16:9 frame AFTER deinterlacing (horizontal scale only)."""
import json, subprocess, os, sys

W = os.path.expanduser("~/Movies/ChampagneSpy_work")
SCR = sys.argv[1]                      # dir holding xNN_scenes.json
PAD43 = {"03", "04"}                   # 4:3 trailers
IDX = dict(P=0, T=1, B=2, M=3)

for n in ["01", "02", "03", "04", "05", "06", "07", "08"]:
    sc = json.load(open(f"{SCR}/x{n}_scenes.json"))["scenes"]
    cmds, last = [], None
    for s in sc:
        k = IDX[s["cls"]]
        if k != last:
            cmds.append(f"{max(0.0, (s['start'] - 0.5) / 25):.4f} streamselect@sel map {k};"); last = k
    cf = f"{W}/scripts/x{n}_cmds.txt"; open(cf, "w").write("\n".join(cmds) + "\n")
    norm = "scale=540:576:flags=lanczos,pad=720:576:90:0:black," if n in PAD43 else ""
    graph = (f"[0:v:0]setpts=N/(25*TB),split=4[p][t][b][m];[p]sendcmd=f='{cf}'[p1];"
             "[t]bwdif=mode=send_frame:parity=tff:deint=all[t1];"
             "[b]bwdif=mode=send_frame:parity=bff:deint=all[b1];"
             "[m]setfield=prog,idet,bwdif=mode=send_frame:parity=auto:deint=interlaced[m1];"
             f"[p1][t1][b1][m1]streamselect@sel=inputs=4:map=0,setfield=prog,{norm}setsar=64/45[out]")
    out = f"{W}/x{n}_master_ffv1.mkv"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-reinit_filter", "0", "-i", f"{W}/x{n}_source.mkv", "-filter_complex", graph,
                    "-map", "[out]", "-fps_mode", "passthrough", "-c:v", "ffv1", "-level", "3", "-g", "1", "-slices", "16",
                    "-slicecrc", "1", "-pix_fmt", "yuv420p", "-y", out], check=True)
    fr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                         "stream=nb_read_packets", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    want = json.load(open(f"{SCR}/x{n}_scenes.json"))["frames"]
    print(f"VTS_{n}: master frames={fr} expected={want} {'OK' if int(fr) == want else 'MISMATCH'}"
          f"{' (pillarboxed 4:3)' if n in PAD43 else ''}", flush=True)
