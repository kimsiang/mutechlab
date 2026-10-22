# mutechlab · 缪子科技实验室

Website for the Muon Technology Laboratory (缪子科技实验室), Tsung-Dao Lee Institute, Shanghai Jiao Tong University.

Company front for MuTechLab muography: one static page, bilingual (中文 / English), styled to match the TDLI Muon Physics Group site (kimsiang.github.io). No build step.

Audiences: infrastructure owners (customers), investors, future hires.

## Structure
- `index.html` — the whole site (styles and scripts inline)
- `assets/fonts/` — self-hosted Space Grotesk, Inter, JetBrains Mono (no Google Fonts, so it loads in mainland China)
- `assets/img/` — tunnel, detector, team and founder photos
- `src/hero.js` — 3D muon tracker hero (three.js); `npm install && npm run build` → `assets/js/hero.bundle.js`
- `build_artifact.py` — makes a single-file copy with assets inlined

## Sections
Hero (3D 256-bar tracker + live event HUD + spec strip) → audience router → 01 Problem → 02 Solutions → 03 Deployments (Outer Ring Tunnel ×2, Chongming Line, Caobao Road, TDLI CMS, Malaysia 2026) → 04 Products & technology (flux monitor, 3D imaging system, CMS, demonstrator; R&D: SHINE accelerator muography, SciFi-MST, AI) → 05 How we work → 06 Feasibility estimator → 07 Investors + milestones → 08 Careers → 09 Founder + FAQ → 10 Contact form

Content sources: kimsiang.github.io research page and news posts (CMS, Outer Ring Tunnel paper, NHEM 2026, Malaysia GCP 2026, CPAC 2026).

## Local preview
Open `index.html` in a browser, or `python3 -m http.server`.

## Deploy
Push to GitHub and enable Pages (Settings → Pages → main / root).

## To edit before going live
- `CONTACT_EMAIL` at the top of the script in index.html
- WeChat QR code image (optional)
