#!/bin/zsh
# Field-matching detectors for the 8 extras (same as the main film): cross-weave comb + local field difference.
cd ~/Movies/ChampagneSpy_work
for n in 01 02 03 04 05 06 07 08; do
  [[ -f scripts/x${n}_crossweave.npy ]] || venv/bin/python scripts/crossweave_blocks.py x${n}_source.mkv scripts/x${n}_crossweave.npy > /dev/null
  [[ -f scripts/x${n}_localdiff.npy ]] || venv/bin/python scripts/localdiff_all.py x${n}_source.mkv scripts/x${n}_localdiff.npy > /dev/null
  echo "x${n} done $(date +%H:%M)"
done
echo ALLDONE
