# mutechlab · 缪子科技实验室

Website for MuTechLab (缪子科技实验室), Shanghai.

Company front for MuTechLab muography: one static page, bilingual (中文 / English). No build step.

Audiences: infrastructure owners (customers), investors, future hires.

## Structure
- `index.html` — the whole site (styles and scripts inline)
- `assets/fonts/` — self-hosted Space Grotesk, Inter, JetBrains Mono (no Google Fonts, so it loads in mainland China)
- `assets/img/` — Outer Ring Tunnel flux figure, CMS detector figure, and `bg/` box backgrounds (lab, detector and film-frame crops; no people, no institutional signage)
- `assets/video/` — the 90 s promo film (principle + application; 1080p 24 MB for desktop, 720p 7 MB served on phones), English narration + 中文字幕, and its poster frame. Source and build instructions: `film/README.md`
- `src/hero.js` — 3D muon tracker hero (three.js); `npm install && npm run build` → `assets/js/hero.bundle.js`
- `build_artifact.py` — makes a single-file copy with assets inlined

## Sections
Hero (3D 256-bar tracker + live event HUD + spec strip) → audience router → 00 Film (90 s promo) → 01 Problem → 02 Solutions → 03 Deployments (Outer Ring Tunnel ×2, Chongming Line, Caobao Road, CMS commissioning, Malaysia 2026) → 04 Products & technology (flux monitor, 3D imaging system, CMS, demonstrator; R&D: SHINE accelerator muography, SciFi-MST, AI) → 05 How we work → 06 Feasibility estimator → 07 Investors + milestones → 08 Careers → 09 FAQ → 10 Contact form


## Local preview
Open `index.html` in a browser, or `python3 -m http.server`.

## Deploy
Push to GitHub and enable Pages (Settings → Pages → main / root).

## To edit before going live
- `CONTACT_EMAIL` and `ICP_NO` at the top of the script in index.html
- Deployment dates for D-02…D-04 (`<time>` in the deployments list) are placeholders — confirm before launch
- WeChat QR code image (optional)
- Names, team photos and institutional affiliation are deliberately left off for now
