"""Assemble the 90 s cut.

Inputs
  render/    plates of scene.py   (30 s edit, used for 0–11 s and 11–27 s → 69–85 s)
  render_p/  plates of scene2.py  (principle act, 58 s)
  voice/voice_stem90.wav + voice/subs90.json  from  narrate.py --texts texts90.toml --duration 90

    python3 compose90.py [--step 3] [--step-p 3] [--skip-post] [--no-gif]

Output: muonlab_promo_90s.mp4 / .gif
"""
import os, sys, glob, json, argparse, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import compose as C
from compose import run, bloom, ease, W, H
from timeline import FPS, f
import timeline90 as T

CYAN = (0, 169, 244)

from fonts_rt import font as rt_font

def post_dir(src, dst):
    files = sorted(glob.glob(os.path.join(src, "*.png"))); os.makedirs(dst, exist_ok=True)
    for i, fp in enumerate(files, 1):
        o = os.path.join(dst, f"{i:04d}.png")
        if not os.path.exists(o): bloom(Image.open(fp).convert("RGB")).save(o, compress_level=3)
    return len(files)

def segment(post, first, last, src_fps, out):
    """Interpolate post frames [first..last] (1-based) to 30 fps 1080p."""
    if os.path.exists(out): return out
    run(["ffmpeg", "-v", "error", "-y", "-start_number", str(first), "-framerate", f"{src_fps:.5f}", "-i", os.path.join(post, "%04d.png"),
         "-frames:v", str(last - first + 1),
         "-vf", f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale={W}:{H}:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-crf", "14", "-preset", "medium", out])
    return out

def title_cards(dst, titles):
    """Top-left title card per step: eyebrow (mono caps, cyan) + zh headline + en line, on a soft dark plate."""
    os.makedirs(dst, exist_ok=True)
    f_eye = rt_font("mono", 24); f_zh = rt_font("zh_b", 60); f_en = rt_font("en", 30, 500)
    items = []
    for i, t in enumerate(titles):
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
        x0, y0 = 110, 96
        d.text((x0 + 22, y0), t["eyebrow"], font=f_eye, fill=CYAN + (255,))
        d.rectangle([x0, y0 + 2, x0 + 8, y0 + 24], fill=CYAN + (255,))
        d.text((x0, y0 + 44), t["zh"], font=f_zh, fill=(255, 255, 255, 255))
        d.text((x0 + 2, y0 + 124), t["en"], font=f_en, fill=(200, 215, 230, 255))
        bb = fr.getbbox(); plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle([bb[0] - 28, bb[1] - 20, bb[2] + 36, bb[3] + 22], radius=12, fill=(2, 8, 16, 120))
        plate.alpha_composite(fr)
        fp = os.path.join(dst, f"title{i:02d}.png"); plate.save(fp, compress_level=3)
        items.append((fp, float(t["from"]), float(t["to"])))
    return items

def subtitle_items(dst, S):
    """Reuse compose.subtitle_frames logic on the 90 s subs."""
    mode = S["subtitles"]
    if mode == "none": return []
    os.makedirs(dst, exist_ok=True)
    f_en = rt_font("en", 42, 500); f_zh = rt_font("zh", 44)
    items = []
    for i, L in enumerate(S["lines"]):
        texts = {"en": [(L["en"], f_en)], "zh": [(L["zh"], f_zh)], "both": [(L["zh"], f_zh), (L["en"], f_en)]}[mode]
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
        lh = 64; yc = int(H * 0.905); y = yc - lh * len(texts) // 2
        for txt, fo in texts:
            bb = d.textbbox((0, 0), txt, font=fo); w = bb[2] - bb[0]; x = (W - w) // 2
            d.rounded_rectangle([x - 22, y - 6, x + w + 22, y + lh - 8], radius=10, fill=(2, 8, 16, 150))
            d.text((x - bb[0], y + (lh - (bb[3] - bb[1])) // 2 - bb[1] - 2), txt, font=fo, fill=(255, 255, 255, 255))
            y += lh
        fp = os.path.join(dst, f"sub{i:02d}.png"); fr.save(fp, compress_level=3)
        items.append((fp, L["start"], L["end"]))
    return items

def logo_frames(dst):
    """Wordmark float-in, same look as the 30 s cut, but timed for the 90 s edit."""
    C.T_LOGO_IN, C.T_WHITE, C.T_END = T.T_LOGO_IN, T.T_WHITE, T.T_END
    return C.overlay_frames(dst)

def mix_audio(S, out="audio_mix90.wav"):
    from scipy.io import wavfile
    import audio as A
    dur = T.DURATION
    m = A.music(dur, t_white=T.T_WHITE, t_cut=3.5, t_image=T.p(T.P_TOMO))
    ev = dict(cut=3.5, thump=6.5, rain=(T.B_START + 1.5, T.B_START + 10), image=17.0 + T.SHIFT, logo=T.T_LOGO_IN, white=T.T_WHITE,
              extra=[("whoosh", T.P_START), ("boom", T.p(T.P_SHOWER + 2.0)), ("ticks", T.p(T.P_ATTEN + 1.5), T.p(T.P_ATTEN + 11)),
                     ("ticks", T.p(T.P_TELE + 1), T.p(T.P_TELE + 11)), ("chord", T.p(T.P_TOMO + 6)), ("whoosh", T.B_START)])
    m = m + A.sfx(dur, ev)
    vp = os.path.join("voice", "voice_stem90.wav")
    if os.path.exists(vp):
        sr, v = wavfile.read(vp); v = v.astype(np.float32) / 32768
        env = np.abs(v); k = int(0.05 * A.SR); env = np.convolve(env, np.ones(k) / k, "same")
        gate = (env > 0.01).astype(np.float32); k2 = int(0.3 * A.SR)
        gate = np.clip(np.convolve(gate, np.ones(k2), "same"), 0, 1); gate = np.convolve(gate, np.ones(k2) / k2, "same")
        g = 10 ** (-S["music_duck"] / 20); m = m * (1 - gate * (1 - g)) + v
    mix = np.tanh(m * 1.2) * 0.9
    wavfile.write(out, A.SR, (mix * 32767).astype(np.int16)); return out

def build(step=3, step_p=3, work="work90", out="muonlab_promo_90s", gif=True, skip_post=False):
    os.makedirs(work, exist_ok=True)
    S = json.load(open(os.path.join("voice", "subs90.json")))
    # --- plates: A (old 0–11 s) + P (principle act) + B (old 11–27 s)
    n_a = post_dir("render", os.path.join("work", "post"))          # shared with the 30 s cut
    n_p = post_dir("render_p", os.path.join(work, "post_p"))
    fa, fp_ = FPS / step, FPS / step_p
    ia = f(T.A_END) // step                                          # plates in old 0–11 s
    segA = segment(os.path.join("work", "post"), 1, ia, fa, os.path.join(work, "segA.mp4"))
    segP = segment(os.path.join(work, "post_p"), 1, n_p, fp_, os.path.join(work, "segP.mp4"))
    segB = segment(os.path.join("work", "post"), ia + 1, n_a, fa, os.path.join(work, "segB.mp4"))
    plates = os.path.join(work, "plates90.mp4")
    if not (skip_post and os.path.exists(plates)):
        lst = os.path.join(work, "concat.txt")
        open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in (segA, segP, segB)))
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", plates])
    # --- overlays
    titles = title_cards(os.path.join(work, "titles"), S.get("titles", []))
    subs = subtitle_items(os.path.join(work, "subs"), S)
    logo_frames(os.path.join(work, "ovl")); C.card_frames(os.path.join(work, "card"), dur=T.T_END - T.T_WHITE + 0.4)
    audio_path = mix_audio(S)
    inputs = ["-i", plates, "-itsoffset", f"{T.T_LOGO_IN}", "-framerate", f"{FPS}", "-i", os.path.join(work, "ovl", "%04d.png"),
              "-framerate", f"{FPS}", "-i", os.path.join(work, "card", "%04d.png"), "-i", audio_path]
    chain = f"[0:v]tpad=stop_mode=clone:stop_duration=2[p];[p][1:v]overlay=format=auto:eof_action=pass,fps={FPS},settb=AVTB,format=yuv420p[v1];"
    prev = "v1"; idx = 4
    for k, (fpng, t0, t1) in enumerate(titles):
        inputs += ["-loop", "1", "-t", f"{t1 - t0:.3f}", "-i", fpng]
        chain += (f"[{idx}:v]format=rgba,fade=in:st=0:d=0.5:alpha=1,fade=out:st={t1 - t0 - 0.5:.3f}:d=0.5:alpha=1,setpts=PTS+{t0}/TB[t{k}];"
                  f"[{prev}][t{k}]overlay=format=auto:eof_action=pass[u{k}];"); prev = f"u{k}"; idx += 1
    for k, (fpng, t0, t1) in enumerate(subs):
        inputs += ["-i", fpng]
        chain += f"[{prev}][{idx}:v]overlay=format=auto:enable='between(t,{t0},{t1})'[s{k}];"; prev = f"s{k}"; idx += 1
    xo = T.T_WHITE - 0.4
    chain += f"[2:v]fps={FPS},settb=AVTB,format=yuv420p[c];[{prev}][c]xfade=transition=fade:duration=0.4:offset={xo}[v]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", chain, "-map", "[v]", "-map", "3:a", "-t", f"{T.T_END}",
         "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "160k", out + ".mp4"])
    if gif:
        run(["ffmpeg", "-v", "error", "-y", "-i", out + ".mp4", "-vf",
             "fps=10,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=5", out + ".gif"])
    for p in (out + ".mp4", out + ".gif"):
        if os.path.exists(p): print(p, round(os.path.getsize(p) / 1e6, 1), "MB")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=3, help="frame step used for render/ (scene.py)")
    ap.add_argument("--step-p", type=int, default=3, help="frame step used for render_p/ (scene2.py)")
    ap.add_argument("--work", default="work90"); ap.add_argument("--out", default="muonlab_promo_90s")
    ap.add_argument("--no-gif", action="store_true"); ap.add_argument("--skip-post", action="store_true")
    a = ap.parse_args()
    build(a.step, a.step_p, a.work, a.out, gif=not a.no_gif, skip_post=a.skip_post)
