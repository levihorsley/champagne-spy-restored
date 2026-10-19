# Deinterlace toolchain (Apple Silicon M5), set up 2026-10-13
- Homebrew: vapoursynth 81, vapoursynth-mvtools, vapoursynth-bestsource, vapoursynth-vszip, av1an, mkvtoolnix, tesseract(+lang)
- Built from source into ../vsplugins: znedi3 (X86=0), fmtconv, vs-removegrain (rgvs)
- Python venv ../venv (python3.14, --system-site-packages): havsfunc==33, mvsfunc (git), adjust (git), vsutil
- havsfunc.py patches (original kept as havsfunc.py.orig):
  1. QTGMC prefilter: focus2.TemporalSoften2 (x86-only) -> std.AverageFrames (max-threshold = plain average), **with scenechange=True** (2026-10-13 22:01) — the pipelines set _SceneChangePrev/_SceneChangeNext from the shot lists, so the scene-cut guard of the original TemporalSoften is kept (QTGMC is fed the whole film, not one scene at a time). Pre-patch copy: havsfunc.py.pre-scenechange.
  2. QTGMC_Interpolate: core.eedi3m.EEDI3 (not built for ARM) -> core.vszip.EEDI3 (port of eedi3m); processes all planes, chroma replaced later when ChromaEdi is set.
- Verified: QTGMC Placebo/Very Slow, SourceMatch=3, Lossless=2, NoiseProcess=0, FPSDivisor 1 (50p) and 2 (25p).
