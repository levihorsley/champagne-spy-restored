#!/bin/bash
# Per-scene target-quality AV1 encode of the deinterlaced master. Resume with: same command + --resume
cd "~/Movies/ChampagneSpy_work"
av1an -i "~/Movies/ChampagneSpy_work/main_master_ffv1.mkv" -o "~/Movies/ChampagneSpy_work/main_av1_video.mkv" \
  --scenes "~/Movies/ChampagneSpy_work/scripts/main_av1an_scenes.json" --chunk-method hybrid --concat mkvmerge \
  --temp "~/Movies/ChampagneSpy_work/av1an_main" --workers 6 --pix-format yuv420p10le \
  -e svt-av1 -v "--preset 2 --tune 0 --input-depth 10 --keyint 300 --scd 0 --enable-variance-boost 0 --enable-qm 0 --film-grain 0 --enable-overlays 0 --lp 3 --color-primaries 5 --transfer-characteristics 6 --matrix-coefficients 5 --color-range 0" \
  --target-quality 95-96 --target-metric vmaf --probing-stat harmonic --qp-range 10-55 \
  --vmaf -y "$@"
