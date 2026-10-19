# The Champagne Spy — 50 fps master pipeline (per-field decisions from scripts/fm_decide.py).
# Every output frame = one field instant. Fields with a same-instant partner are woven (exact disc lines);
# all others come from QTGMC (Placebo, SourceMatch=3, Lossless=1 = exact disc lines, TR2=1 = light smoothing, no denoise), TFF or BFF per shot.
# Optional vspipe args: start/end = SOURCE frame range (output = slots 2*start .. 2*end).
import os, sys, numpy as np, vapoursynth as vs
c = vs.core
W = os.path.expanduser("~/Movies/ChampagneSpy_work")
for p in ("vsznedi3.so", "libfmtconv.dylib", "libremovegrain.dylib"): c.std.LoadPlugin(f"{W}/vsplugins/{p}")
sys.path.insert(0, f"{W}/scripts")
import havsfunc as haf
from fm_common import load
clip = c.bs.VideoSource(f"{W}/main_source.mkv")
N = clip.num_frames
# scene-cut markers from the shot list, so QTGMC's temporal prefilter never averages across a cut (as original QTGMC)
import json
_starts = {s["start"] for s in json.load(open(f"{W}/scripts/main_shots_interlace.json"))}
def _sc(n, f):
    f = f.copy(); f.props["_SceneChangePrev"] = int(n in _starts); f.props["_SceneChangeNext"] = int(n + 1 in _starts); return f
clip = c.std.ModifyFrame(clip, clip, _sc)
code = np.load(f"{W}/scripts/main_fieldmatch.npy")[0].astype(np.int64)
tff = np.repeat(load()["tff"], 2)
def prog(x): return c.std.RemoveFrameProps(c.std.SetFieldBased(x, 0), ["_Field"])
def cross(t):
    s = c.std.SetFieldBased(clip, 2 if t else 1)
    return prog(c.std.SelectEvery(c.std.DoubleWeave(c.std.SeparateFields(s, tff=t), tff=t), 2, 1))
def q(t): return prog(haf.QTGMC(c.std.SetFieldBased(clip, 2 if t else 1), Preset="Placebo", TFF=t, FPSDivisor=1,
                               SourceMatch=3, Lossless=1, TR2=1, NoiseProcess=0))
own = prog(c.std.Interleave([clip, clip]))                            # slot s -> source frame s//2
X, Y = cross(True), cross(False)
nxtT, nxtB = c.std.Interleave([X, X]), c.std.Interleave([Y, Y])       # slot s -> pair (s//2, s//2+1)
pad = c.std.BlankClip(own, length=2)
prvT, prvB = pad + nxtT[:-2], pad + nxtB[:-2]                         # slot s -> pair (s//2-1, s//2)
def qc(t): return prog(haf.QTGMC(c.std.SetFieldBased(clip, 2 if t else 1), Preset="Placebo", TFF=t, FPSDivisor=1,
                                SourceMatch=3, Lossless=2, NoiseProcess=0))   # 'clean' rebuild for shots picked by qtgmc_choose.py
clips = [q(True), prvT, own, nxtT, q(False), prvB, nxtB, qc(True), qc(False)]
sel = np.where(tff, code, np.array([4, 5, 2, 6])[code])
CH = f"{W}/scripts/main_qtgmc_choice.npy"
if os.path.exists(CH): sel = np.where(np.load(CH).astype(bool), np.where(tff, 7, 8), sel)
out = c.std.FrameEval(own, lambda n: clips[sel[n]])
out = c.std.AssumeFPS(out, fpsnum=50, fpsden=1)
g = globals()
a, b = int(g.get("start", 0)), int(g.get("end", N))
out[2 * a:2 * b].set_output(0)
