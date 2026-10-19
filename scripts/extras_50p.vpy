# The Champagne Spy — 50 fps masters for the extras, same per-field method as the film (scripts/main_50p.vpy).
# vspipe arg: which=intros | 07 | 08
#   intros = 01 copyright card + 02 Neue Visionen logo + 03..06 trailers, joined (chapters in scripts/intro_chapters.txt)
#   03/04 are letterboxed widescreen inside 4:3 frames -> crop the bars, scale to fill the 16:9 frame (Levi's call)
import os, sys, json, numpy as np, vapoursynth as vs
c = vs.core
W = os.path.expanduser("~/Movies/ChampagneSpy_work")
for p in ("vsznedi3.so", "libfmtconv.dylib", "libremovegrain.dylib"): c.std.LoadPlugin(f"{W}/vsplugins/{p}")
sys.path.insert(0, f"{W}/scripts")
import havsfunc as haf
from fm_common import load
CROP = {"03": dict(left=4, right=4, top=74, bottom=74),    # 1.78:1 picture, 712x428 active
        "04": dict(left=0, right=0, top=84, bottom=60)}    # 1.66:1 picture (rows 60-515), trimmed to 720x432 = 16:9 from the TOP only: its burned-in subtitles reach row 510
def prog(x): return c.std.RemoveFrameProps(c.std.SetFieldBased(x, 0), ["_Field"])
def piece(n):
    clip = c.bs.VideoSource(f"{W}/x{n}_source.mkv")
    starts = {s["start"] for s in json.load(open(f"{W}/scripts/x{n}_scenes.json"))["scenes"]}
    def sc(n, f, starts=starts):
        f = f.copy(); f.props["_SceneChangePrev"] = int(n in starts); f.props["_SceneChangeNext"] = int(n + 1 in starts); return f
    clip = c.std.ModifyFrame(clip, clip, sc)
    code = np.load(f"{W}/scripts/x{n}_fieldmatch.npy")[0].astype(np.int64); tff = np.repeat(load(f"x{n}")["tff"], 2)
    def cross(t):
        s = c.std.SetFieldBased(clip, 2 if t else 1)
        return prog(c.std.SelectEvery(c.std.DoubleWeave(c.std.SeparateFields(s, tff=t), tff=t), 2, 1))
    def q(t): return prog(haf.QTGMC(c.std.SetFieldBased(clip, 2 if t else 1), Preset="Placebo", TFF=t, FPSDivisor=1,
                                   SourceMatch=3, Lossless=1, TR2=1, NoiseProcess=0))
    own = prog(c.std.Interleave([clip, clip])); X, Y = cross(True), cross(False)
    nxtT, nxtB = c.std.Interleave([X, X]), c.std.Interleave([Y, Y]); pad = c.std.BlankClip(own, length=2)
    clips = [q(True), pad + nxtT[:-2], own, nxtT, q(False), pad + nxtB[:-2], nxtB]
    sel = np.where(tff, code, np.array([4, 5, 2, 6])[code])
    out = c.std.FrameEval(own, lambda n, clips=clips, sel=sel: clips[sel[n]])
    if n in CROP: out = c.resize.Spline36(c.std.Crop(out, **CROP[n]), 720, 576)
    out = c.std.SetFrameProps(out, _SARNum=64, _SARDen=45)
    return c.std.AssumeFPS(out, fpsnum=50, fpsden=1)
which = str(globals().get("which", "intros"))
out = c.std.Splice([piece(n) for n in ("01", "02", "03", "04", "05", "06")]) if which == "intros" else piece(which)
out.set_output(0)
