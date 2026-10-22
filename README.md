# mutechlab · 缪子科技实验室

Website for the Muon Technology Laboratory (缪子科技实验室), Tsung-Dao Lee Institute, Shanghai Jiao Tong University.

Single static page, bilingual (中文 / English), no build step.

## Structure
- `index.html` — the whole site (styles and scripts inline)

## Sections (muography, customer-facing)
1. Hero — river-tunnel scene with falling muons
2. Why muography — comparison with boreholes, radar, sonar
3. Solutions — field-proven vs pilot-available settings
4. Case study — Shanghai Outer Ring Tunnel (J. Appl. Phys. 138, 114902, 2025)
5. Deliverables
6. How we work — 5-step engagement
7. Feasibility estimator — measurement time for a given depth, material, change and detector area
8. FAQ
9. About us
10. Inquiry form — builds a copyable project summary

## Local preview
Open `index.html` in a browser, or `python3 -m http.server`.

## Deploy
Push to GitHub and enable Pages (Settings → Pages → main / root).

## To edit before going live
- `CONTACT_EMAIL` at the top of the script in index.html
- `PAPER_URL` if you prefer the journal DOI over arXiv
- WeChat QR code image (optional)
