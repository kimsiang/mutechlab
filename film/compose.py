"""Post: bloom + upscale the Blender plates, interpolate to 30 fps, overlay the
wordmark, add the white end card, mix audio, encode MP4 (<40 MB) and GIF.

    python3 compose.py --frames render --step 3 --out muonlab_promo_30s
"""
import os, sys, glob, argparse, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter, zoom
from timeline import *
from logo import load_logo, NAVY
from fonts_rt import font as rt_font

W, H = 1920, 1080

def run(cmd):
    print("$", " ".join(cmd)[:160], flush=True)
    subprocess.run(cmd, check=True)

def bloom(img, thr=0.75, sigma=9, amount=0.55):
    a = np.asarray(img).astype(np.float32) / 255
    lum = a.max(axis=2)
    hi = a * np.clip((lum - thr) / (1 - thr), 0, 1)[..., None]
    small = hi[::4, ::4]
    bl = gaussian_filter(small, (sigma, sigma, 0))
    bl = zoom(bl, (4, 4, 1), order=1)[:a.shape[0], :a.shape[1]]
    out = np.clip(a + bl * amount, 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8))

def ease(p): return 0.5 - 0.5 * math.cos(math.pi * min(max(p, 0), 1))

def post_frames(src, dst, step):
    """Renumber the rendered (stepped) frames 1..N, add bloom. Returns N and source fps."""
    files = sorted(glob.glob(os.path.join(src, "*.png")))
    os.makedirs(dst, exist_ok=True)
    for i, fp in enumerate(files, 1):
        o = os.path.join(dst, f"{i:04d}.png")
        if os.path.exists(o): continue
        bloom(Image.open(fp).convert("RGB")).save(o, compress_level=3)
    return len(files), FPS / step

def overlay_frames(dst):
    """RGBA wordmark frames for t in [T_LOGO_IN, T_WHITE+0.5): float-in like the GSCAN card."""
    os.makedirs(dst, exist_ok=True)
    logo = load_logo()
    base_w = int(W * 0.62)
    n = f(T_WHITE + 0.5) - f(T_LOGO_IN)
    for i in range(n):
        t = i / FPS
        p = ease(t / 0.7)
        s = 1.14 - 0.14 * p
        a = p
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        w = int(base_w * s); h = int(logo.height * w / logo.width)
        lg = logo.resize((w, h), Image.LANCZOS)
        # white soft plate behind the mark for legibility, like a frosted panel
        al = lg.split()[3].point(lambda v: int(v * a))
        # soft white halo behind the mark for legibility over the scene
        halo = Image.new("RGBA", lg.size, (255, 255, 255, 0)); halo.putalpha(al.point(lambda v: int(v * 0.85)))
        halo = halo.filter(ImageFilter.GaussianBlur(w * 0.012))
        lg.putalpha(al)
        pos = ((W - w) // 2, (H - h) // 2 - 20)
        fr.alpha_composite(halo, pos); fr.alpha_composite(halo, pos); fr.alpha_composite(lg, pos)
        fr.save(os.path.join(dst, f"{i+1:04d}.png"), compress_level=3)
    return n

def card_frames(dst, dur=T_END - T_WHITE + 0.4):
    """White end card: wordmark settles, tagline rises."""
    os.makedirs(dst, exist_ok=True)
    logo = load_logo()
    f_cn = rt_font("zh", 44)
    f_en = rt_font("en", 26, 500)
    INK = (33, 43, 62)
    n = int(round(dur * FPS))
    base_w = int(W * 0.52)
    for i in range(n):
        t = i / FPS
        fr = Image.new("RGB", (W, H), (255, 255, 255))
        p = ease(t / 0.8)
        s = 0.96 + 0.04 * p
        w = int(base_w * s); h = int(logo.height * w / logo.width)
        lg = logo.resize((w, h), Image.LANCZOS)
        lg.putalpha(lg.split()[3].point(lambda v: int(v * p)))
        fr.paste(lg, ((W - w) // 2, (H - h) // 2 - 70), lg)
        d = ImageDraw.Draw(fr)
        q = ease((t - 0.5) / 0.8)
        col = tuple(int(255 - (255 - c) * q) for c in INK)
        y0 = (H + h) // 2 - 40 + int(20 * (1 - q))
        for txt, fnt, dy in (("看见看不见的世界", f_cn, 0), ("Seeing the unseen with muons", f_en, 64)):
            bb = d.textbbox((0, 0), txt, font=fnt)
            d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y0 + dy), txt, font=fnt, fill=col)
        fr.save(os.path.join(dst, f"{i+1:04d}.png"), compress_level=3)
    return n

def subtitle_frames(dst):
    """One RGBA PNG per narration line: centred text on a soft dark plate near the bottom (reference style)."""
    import json
    p = os.path.join("voice", "subs.json")
    if not os.path.exists(p): return []
    S = json.load(open(p)); mode = S["subtitles"]
    if mode == "none": return []
    os.makedirs(dst, exist_ok=True)
    f_en = rt_font("en", 42, 500)
    f_zh = rt_font("zh", 44)
    items = []
    for i, L in enumerate(S["lines"]):
        texts = {"en": [(L["en"], f_en)], "zh": [(L["zh"], f_zh)], "both": [(L["zh"], f_zh), (L["en"], f_en)]}[mode]
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fr)
        lh = 64; yc = int(H * 0.905); y = yc - lh * len(texts) // 2
        for txt, f in texts:
            bb = d.textbbox((0, 0), txt, font=f); w = bb[2] - bb[0]; x = (W - w) // 2
            d.rounded_rectangle([x - 22, y - 6, x + w + 22, y + lh - 8], radius=10, fill=(2, 8, 16, 150))
            d.text((x - bb[0], y + (lh - (bb[3] - bb[1])) // 2 - bb[1] - 2), txt, font=f, fill=(255, 255, 255, 255))
            y += lh
        fp = os.path.join(dst, f"sub{i:02d}.png"); fr.save(fp, compress_level=3)
        items.append((fp, L["start"], L["end"]))
    return items

def mix_audio(out="audio_mix.wav"):
    """Music + SFX from audio.py, ducked under the narration stem."""
    import json
    from scipy.io import wavfile
    import audio as A
    m = A.music() + A.sfx()
    vp = os.path.join("voice", "voice_stem.wav")
    if os.path.exists(vp):
        sr, v = wavfile.read(vp); v = v.astype(np.float32) / 32768
        duck_db = json.load(open(os.path.join("voice", "subs.json")))["music_duck"]
        env = np.abs(v); k = int(0.05 * A.SR); env = np.convolve(env, np.ones(k) / k, "same")
        gate = (env > 0.01).astype(np.float32)
        # widen the gate 0.3 s each side and smooth it
        k2 = int(0.3 * A.SR); gate = np.clip(np.convolve(gate, np.ones(k2), "same"), 0, 1)
        gate = np.convolve(gate, np.ones(k2) / k2, "same")
        g = 10 ** (-duck_db / 20)
        m = m * (1 - gate * (1 - g)) + v * 1.0
    mix = np.tanh(m * 1.2) * 0.9
    wavfile.write(out, A.SR, (mix * 32767).astype(np.int16))
    return out

def build(frames, step, out, work="work", gif=True, skip_post=False):
    os.makedirs(work, exist_ok=True)
    n, src_fps = post_frames(frames, os.path.join(work, "post"), step)
    print(f"{n} plates at {src_fps:.2f} fps")
    plates = os.path.join(work, "plates.mp4")
    if not (skip_post and os.path.exists(plates)): run(["ffmpeg", "-v", "error", "-y", "-framerate", f"{src_fps:.5f}", "-i", os.path.join(work, "post", "%04d.png"),
         "-vf", f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale={W}:{H}:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-crf", "14", "-preset", "medium", plates])
    overlay_frames(os.path.join(work, "ovl"))
    card_frames(os.path.join(work, "card"))
    audio_path = mix_audio()
    subs = subtitle_frames(os.path.join(work, "subs"))
    xo = T_WHITE - 0.4
    sub_inputs = []; sub_chain = ""; prev = "v1"
    for k, (fp, t0, t1) in enumerate(subs):
        sub_inputs += ["-i", fp]
        idx = 4 + k
        sub_chain += f"[{prev}][{idx}:v]overlay=format=auto:enable='between(t,{t0},{t1})'[s{k}];"; prev = f"s{k}"

    run(["ffmpeg", "-v", "error", "-y",
         "-i", plates,
         "-itsoffset", f"{T_LOGO_IN}", "-framerate", f"{FPS}", "-i", os.path.join(work, "ovl", "%04d.png"),
         "-framerate", f"{FPS}", "-i", os.path.join(work, "card", "%04d.png"),
         "-i", audio_path, *sub_inputs,
         "-filter_complex",
         f"[0:v]tpad=stop_mode=clone:stop_duration=1[p];[p][1:v]overlay=format=auto:eof_action=pass,fps={FPS},settb=AVTB,format=yuv420p[v1];"
         + sub_chain +
         f"[2:v]fps={FPS},settb=AVTB,format=yuv420p[c];[{prev}][c]xfade=transition=fade:duration=0.4:offset={xo}[v]",
         "-map", "[v]", "-map", "3:a", "-t", f"{T_END}",
         "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "160k", out + ".mp4"])
    if gif:
        run(["ffmpeg", "-v", "error", "-y", "-i", out + ".mp4",
             "-vf", "fps=12,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=5",
             out + ".gif"])
    for p in (out + ".mp4", out + ".gif"):
        if os.path.exists(p): print(p, round(os.path.getsize(p) / 1e6, 1), "MB")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="render"); ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--out", default="muonlab_promo_30s"); ap.add_argument("--work", default="work")
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--skip-post", action="store_true", help="reuse work/plates.mp4 (narration/subtitle changes only)")
    a = ap.parse_args()
    build(a.frames, a.step, a.out, a.work, gif=not a.no_gif, skip_post=a.skip_post)
