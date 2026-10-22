#!/bin/bash
# One-click build on a Mac (Apple Silicon, Cycles + Metal).  See README.md.
#   ./run_mac.sh 90          full-quality 90 s cut  (1080p, every frame, 64 samples; ~2–3 h on an M-series GPU)
#   ./run_mac.sh 90 fast     preview-quality 90 s cut (720p, every 3rd frame, 12 samples; ~30–40 min)
#   ./run_mac.sh 30 [fast]   the 30 s cut only
set -e
cd "$(dirname "$0")"
CUT="${1:-90}"; Q="${2:-hq}"
command -v ffmpeg >/dev/null || { echo "need ffmpeg:  brew install ffmpeg"; exit 1; }
# bpy 5.2 only ships wheels for Python 3.13 -> use a private 3.13 venv (installed with brew if missing)
PY313=$(command -v python3.13 || true)
if [ -z "$PY313" ]; then
  command -v brew >/dev/null || { echo "need Python 3.13:  brew install python@3.13"; exit 1; }
  echo "installing python@3.13 with Homebrew ..."; brew install -q python@3.13
  PY313="$(brew --prefix python@3.13)/bin/python3.13"
fi
[ -x .venv/bin/python ] || "$PY313" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q bpy==5.2.2 pillow numpy scipy soundfile
python3() { ./.venv/bin/python "$@"; }   # every python3 below is the venv
DEV="${BLENDER_DEVICE:-METAL}"
if [ "$Q" = "fast" ]; then STEP=3; RES="1280 720"; SMP=12; else STEP=1; RES="1920 1080"; SMP=64; fi

python3 scene.py  --step $STEP --res $RES --samples $SMP --out render   --device $DEV      # 30 s plates (0–27 s)
if [ "$CUT" = "90" ]; then
  python3 scene2.py --step $STEP --res $RES --samples $SMP --out render_p --device $DEV    # principle act (58 s)
  python3 narrate.py --texts texts90.toml --duration 90 || { ./setup_voice.sh && python3 narrate.py --texts texts90.toml --duration 90; }
  python3 compose90.py --step $STEP --step-p $STEP
  echo "done: muonlab_promo_90s.mp4 / .gif"
else
  python3 narrate.py || { ./setup_voice.sh && python3 narrate.py; }
  python3 compose.py --frames render --step $STEP
  echo "done: muonlab_promo_30s.mp4 / .gif"
fi
