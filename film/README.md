# 缪子科技实验室 · promo film (30 s and 90 s)

Everything is generated from code: the 3D scenes are built and rendered by Blender (`bpy` 5.2, Cycles), the
narration is an offline neural voice, the music is synthesised, and ffmpeg assembles the result.
No hand-modelled assets except `logo.png`.

## Render the MP4 on a Mac (Apple Silicon)

One time:

```bash
brew install ffmpeg                       # if you don't have it
git clone https://github.com/kimsiang/mutechlab && cd mutechlab/film
```

(`./setup_voice.sh` installs the offline guide voice, ~350 MB. You only need it if you change narration text:
the audio for the current script is already in `voice/_cache/`, and `run_mac.sh` skips the download when nothing
has to be re-spoken.)

Then:

```bash
./run_mac.sh 90 fast      # preview: 720p, every 3rd frame interpolated → muonlab_promo_90s.mp4   (~30–40 min)
./run_mac.sh 90           # final:   1080p, every frame, 64 samples    → muonlab_promo_90s.mp4   (~2–3 h)
./run_mac.sh 30           # the 30 s cut only                           → muonlab_promo_30s.mp4
```

`run_mac.sh` installs the Python packages it needs (`bpy`, `pillow`, `numpy`, `scipy`, `soundfile`,
`sherpa-onnx`), renders with Cycles on the GPU (`BLENDER_DEVICE=CPU ./run_mac.sh 90` to force CPU), and
is resumable: rendered frames in `render/` and `render_p/` are kept, so if it stops you just run it again.
Python 3.11–3.13 is required by `bpy`.

When it finishes, copy `muonlab_promo_90s.mp4` into the website as `../assets/video/mutechlab-film-90s.mp4`
(or just push it and say so) — the page expects that path.

Doing the steps by hand, which is what the script does:

```bash
python3 scene.py  --step 1 --res 1920 1080 --samples 64 --out render   --device METAL   # 30 s plates (0–27 s)
python3 scene2.py --step 1 --res 1920 1080 --samples 64 --out render_p --device METAL   # principle act (58 s)
python3 narrate.py --texts texts90.toml --duration 90                                   # voice stem + subtitles
python3 compose90.py --step 1 --step-p 1                                                 # bloom, overlays, audio → MP4 + GIF
```

`--step 3` renders every third frame and `compose90.py --step 3 --step-p 3` interpolates the rest (what the
preview uses). The renders are the slow part; everything after `narrate.py` takes about three minutes and
does not need a re-render, so edit text freely.

## Files

| file | what it does |
|---|---|
| `timeline.py`, `timeline90.py` | shot timings of the 30 s and 90 s cuts (single source of truth) |
| `scene.py` | city cutaway: street, strata, pipes, metro tunnel, muon telescope, muon rain, muography image, camera path |
| `scene2.py` | principle act: cosmic-ray shower → attenuation (thin / thick / cavity) → telescope under a hill → multi-view tomography |
| `texts.toml`, `texts90.toml` | narration lines (中文 + English), start times, title cards, voice/subtitle language |
| `narrate.py` | your recordings in `voice/<lang>/<id>.wav` first, else the offline Kokoro guide voice; writes the voice stem + subtitle schedule |
| `audio.py` | original music + SFX (numpy) |
| `compose.py`, `compose90.py` | bloom, 1080p upscale, frame interpolation to 30 fps, title cards, subtitles, wordmark, white end card, audio mix, MP4 + GIF |
| `logo.py`, `vectorize_logo.py`, `logo.png` | the wordmark (traced from `logo_src.png`); `logo.png` is what the film uses |
| `fonts_rt.py`, `fonts/` | bundled fonts so text renders identically on macOS and Linux |
| `setup_voice.sh`, `run_mac.sh` | guide-voice install; one-click build |

## 90 s shot list

| time | scene | narration |
|---|---|---|
| 0–11 | street → crane down into the earth cutaway | hook: pipes, strata, cavities, tunnel |
| 11–23 | **Step 1** cosmic-ray shower over the skyline, muons reach the ground | 15 km up; ~10⁴ muons / m² / min |
| 23–37 | **Step 2** three rock columns (thin / thick / cavity), muons absorbed or passing | more matter → fewer muons; a cavity lets more through |
| 37–51 | **Step 3** telescope in a chamber under a hill, muons from many directions | count by direction, compare with open sky |
| 51–69 | **Step 4** three telescopes, crossing rays, voxels light up | combine views like a CT → 3-D density; "muon transmission tomography" |
| 69–85 | back in the metro tunnel: detector, muon rain, muography image, pull back | application; wordmark floats in at 82 s |
| 85–90 | white end card | 缪子科技实验室 · 看见看不见的世界 |

## Narration and subtitles

Edit `texts90.toml` (`voice = "en"` or `"zh"`, `subtitles = "zh"` / `"en"` / `"both"`), then
`python3 narrate.py --texts texts90.toml --duration 90 && python3 compose90.py --skip-post`.
To use your own voice, record each line as `voice/en/<id>.wav` or `voice/zh/<id>.wav` (prompt sheet:
`voice/RECORDING_SCRIPT90.md`); the guide voice fills in any line you have not recorded.
Guide-voice audio for the current script is cached in `voice/_cache/`.

## Swap the logo

Replace `logo.png` (transparent PNG, any size ≥ 1000 px wide) and run `compose90.py --skip-post`.
