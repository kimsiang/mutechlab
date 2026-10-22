"""Narration: reads texts.toml, synthesises missing lines with the offline Kokoro guide voice (sherpa-onnx),
prefers your own recordings in voice/<lang>/<id>.*, lays the lines on the 30 s timeline, and writes
  voice/voice_stem.wav        the spoken track (48 kHz mono)
  voice/subs.json             [{start, end, zh, en}] for compose.py to burn in
  voice/RECORDING_SCRIPT.md   prompt sheet if you want to record the lines yourself
"""
import os, sys, json, glob, hashlib, subprocess, tomllib
import numpy as np
from scipy.io import wavfile
from timeline import DURATION

HERE = os.path.dirname(os.path.abspath(__file__))
VDIR = os.path.join(HERE, "voice"); CACHE = os.path.join(VDIR, "_cache")
MODEL = os.path.join(VDIR, "models", "kokoro-multi-lang-v1_0")
SR = 48000; GAP = 0.25

TEXTS = "texts.toml"; OUT = ""   # OUT = suffix for voice_stem/subs ("" or "90")
def load():
    with open(os.path.join(HERE, TEXTS), "rb") as f:
        return tomllib.load(f)

def read48(path):
    tmp = path + ".48k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", tmp], check=True)
    sr, x = wavfile.read(tmp); os.remove(tmp)
    x = x.astype(np.float32) / 32768
    nz = np.where(np.abs(x) > 0.01)[0]
    if len(nz): x = x[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.08 * SR)]
    return x / max(1e-6, np.abs(x).max()) * 0.9

_tts = None
def guide(line, lang, S):
    """Kokoro via sherpa-onnx. Chinese voices zf_*/zm_*, English af_*/am_*/bf_*/bm_*."""
    global _tts
    text = line.get("tts", line[lang]) if lang == "zh" else line["en"]
    voice = S["guide_voice"] if lang == "zh" else S.get("guide_voice_en", "af_heart")
    key = hashlib.sha1(f"{text}|{voice}|{S['guide_speed']}".encode()).hexdigest()[:10]
    out = os.path.join(CACHE, f"guide_{lang}_{line['id']}_{key}.wav")
    if os.path.exists(out): return out
    if not os.path.exists(os.path.join(MODEL, "model.onnx")):
        sys.exit(f"  line {line['id']} needs the guide voice and no cached audio matches its text: run ./setup_voice.sh")
    import sherpa_onnx, soundfile as sf
    if _tts is None:
        d = MODEL
        cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=f"{d}/model.onnx", voices=f"{d}/voices.bin", tokens=f"{d}/tokens.txt", data_dir=f"{d}/espeak-ng-data",
            dict_dir=f"{d}/dict", lexicon=f"{d}/lexicon-zh.txt,{d}/lexicon-us-en.txt"), num_threads=2), max_num_sentences=1)
        _tts = sherpa_onnx.OfflineTts(cfg)
    names = {}
    import onnx
    for p in onnx.load(f"{MODEL}/model.onnx", load_external_data=False).metadata_props:
        if p.key == "speaker2id":
            names = {k: int(v) for k, v in (kv.split("->") for kv in p.value.split(","))}
    a = _tts.generate(text, sid=names.get(voice, 47), speed=float(S["guide_speed"]))
    os.makedirs(CACHE, exist_ok=True); sf.write(out, a.samples, a.sample_rate)
    return out

def source(line, lang, S):
    for ext in ("wav", "m4a", "mp3", "aiff", "flac"):
        p = os.path.join(VDIR, lang, f"{line['id']}.{ext}")
        if os.path.exists(p): return p, "recording"
    g = guide(line, lang, S)
    return g, "guide"

def build(duration=DURATION):
    T = load(); S = T["settings"]; lang = S["voice"]; DURATION_ = duration
    stem = np.zeros(int(DURATION_ * SR), np.float32); subs = []; t_prev_end = 0.0
    for line in T["voice"]:
        at = float(line["at"]); dur = 0.0
        if lang != "none":
            src, kind = source(line, lang, S)
            if src:
                x = read48(src); dur = len(x) / SR
                if at < t_prev_end + GAP - 1e-6:
                    print(f"  {line['id']}: pushed {at:.2f} -> {t_prev_end + GAP:.2f} s (overlap)"); at = t_prev_end + GAP
                i = int(at * SR); j = min(len(stem), i + len(x)); stem[i:j] += x[:j - i]
                print(f"  {line['id']:10s} {at:5.2f}s  {dur:4.2f}s  {kind}")
        end = at + max(dur, 1.8) + 0.3
        subs.append({"start": round(at, 3), "end": round(min(end, DURATION_), 3), "zh": line["zh"], "en": line["en"]})
        t_prev_end = at + dur
    os.makedirs(VDIR, exist_ok=True)
    wavfile.write(os.path.join(VDIR, f"voice_stem{OUT}.wav"), SR, (np.clip(stem, -1, 1) * 32767).astype(np.int16))
    json.dump({"subtitles": S["subtitles"], "music_duck": S["music_duck"], "lines": subs, "titles": T.get("title", [])},
              open(os.path.join(VDIR, f"subs{OUT}.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(VDIR, f"RECORDING_SCRIPT{OUT}.md"), "w") as f:
        f.write("# 录音提词表 · 缪子科技实验室 30 秒宣传片\n\n每句录成 voice/zh/<id>.wav（或 m4a/mp3），然后运行 `python3 narrate.py && python3 compose.py --skip-post`。\n\n")
        f.write("| id | 开始 | 中文 | English |\n|---|---|---|---|\n")
        for s, l in zip(subs, T["voice"]): f.write(f"| `{l['id']}` | {s['start']:.1f} s | {l['zh']} | {l['en']} |\n")
    print("voice/voice_stem.wav, voice/subs.json written")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--texts", default="texts.toml"); ap.add_argument("--duration", type=float, default=DURATION)
    a = ap.parse_args(); TEXTS = a.texts; OUT = "90" if a.texts.endswith("90.toml") else ""
    build(a.duration)
