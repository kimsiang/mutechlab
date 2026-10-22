#!/bin/bash
# Installs the offline guide voice (Kokoro-82M multi-lang via sherpa-onnx; Mandarin + English, Apache-2.0).
# Only needed to re-speak lines you changed in texts.toml and have not recorded yourself.
set -e; cd "$(dirname "$0")"
PY=./.venv/bin/python; [ -x $PY ] || PY=python3
$PY -m pip install -q sherpa-onnx soundfile onnx 2>/dev/null || $PY -m pip install -q --break-system-packages sherpa-onnx soundfile onnx
mkdir -p voice/models && cd voice/models
if [ ! -f kokoro-multi-lang-v1_0/model.onnx ]; then
  echo "Downloading the voice model (~350 MB) ..."
  curl -sSL -C - --retry 5 -o k.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
  tar xjf k.tar.bz2 && rm k.tar.bz2
fi
echo "Guide voice ready."
