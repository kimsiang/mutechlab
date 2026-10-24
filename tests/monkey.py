#!/usr/bin/env python3
"""Monkey test for the MuTechLab single-page site.

Serves the repo root on a local port, then for each (viewport, seed) runs a
burst of random user actions — clicks, taps, typing junk/unicode/injection
strings, slider abuse, select changes, key mashing, scrolling, resizing,
language toggles, back/forward — and records anything that breaks:

  * uncaught JS exceptions (pageerror)
  * console.error / console.warn
  * failed or 4xx/5xx requests
  * NaN / Infinity / undefined / null / [object leaking into visible text
  * horizontal page overflow
  * unexpected navigation away from the page

Usage: python3 tests/monkey.py [--actions N] [--seeds a,b,c] [--out DIR]
"""
import argparse, functools, http.server, json, os, random, re, socketserver, threading, time
from playwright.sync_api import sync_playwright, Error as PWError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JUNK = [
    "", " ", "a", "测试缪子成像", "مرحبا", "🙂🚀💥", "0", "-1", "1e309", "NaN",
    "<script>alert(1)</script>", "\"><img src=x onerror=alert(1)>", "'; DROP TABLE x;--",
    "A" * 5000, "\n\n\n", "%s%s%n", "../../etc/passwd", "user@example", "a@b.c",
    "javascript:alert(1)", "‮RTL override", "\u0000null",
]
KEYS = ["Tab", "Shift+Tab", "Enter", "Escape", " ", "ArrowUp", "ArrowDown",
        "ArrowLeft", "ArrowRight", "Home", "End", "PageDown", "PageUp", "Backspace"]
VIEWPORTS = {
    "desktop": dict(viewport={"width": 1440, "height": 900}),
    "tablet":  dict(viewport={"width": 820, "height": 1180}, has_touch=True),
    "mobile":  dict(viewport={"width": 375, "height": 740}, has_touch=True,
                    is_mobile=True, device_scale_factor=2),
}
BAD_TEXT = re.compile(r"\b(NaN|Infinity|undefined)\b|\[object |\bnull\b(?! hypothesis)")


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    handler.log_message = lambda *a: None
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/index.html"


def checks(page):
    return page.evaluate("""() => {
      const out = {};
      const de = document.documentElement;
      out.overflowX = Math.max(de.scrollWidth, document.body.scrollWidth) - window.innerWidth;
      if (out.overflowX > 1) {
        const w = window.innerWidth, offenders = [];
        for (const el of document.querySelectorAll('body *')) {
          const r = el.getBoundingClientRect();
          if (r.right > w + 1 && r.width > 0 && getComputedStyle(el).position !== 'fixed') {
            offenders.push((el.id ? '#' + el.id : el.tagName.toLowerCase() +
              (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''))
              + ` right=${Math.round(r.right)}`);
            if (offenders.length > 6) break;
          }
        }
        out.offenders = offenders;
      }
      out.text = document.body.innerText;
      return out;
    }""")


def run(pw, url, vp_name, seed, n_actions, outdir):
    rng = random.Random(seed)
    browser = pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
    ctx = browser.new_context(**VIEWPORTS[vp_name])
    # never let mailto / external links leave the sandbox
    ctx.route(re.compile(r"^(?!http://127\.0\.0\.1).*"), lambda r: r.abort())
    page = ctx.new_page()
    issues = []
    log = []

    def add(kind, msg):
        key = (kind, msg[:300])
        if key not in {(i["kind"], i["msg"][:300]) for i in issues}:
            issues.append({"kind": kind, "msg": msg[:1000], "after": log[-3:]})

    page.on("pageerror", lambda e: add("pageerror", f"{e.name}: {e.message}\n{(e.stack or '')[:600]}"))
    page.on("console", lambda m: m.type in ("error", "warning") and add("console." + m.type, m.text))
    page.on("requestfailed", lambda r: r.url.startswith("http://127.0.0.1") and add("requestfailed", f"{r.url} {r.failure}"))
    page.on("response", lambda r: r.status >= 400 and add("http", f"{r.status} {r.url}"))
    page.on("dialog", lambda d: (add("dialog", f"{d.type}: {d.message}"), d.dismiss()))

    page.goto(url, wait_until="load")
    page.wait_for_timeout(1500)
    baseline = set(BAD_TEXT.findall(checks(page)["text"]))
    W, H = page.viewport_size["width"], page.viewport_size["height"]

    def act():
        r = rng.random()
        if r < 0.28:   # click/tap random point
            x, y = rng.randrange(W), rng.randrange(H)
            log.append(f"click({x},{y})")
            (page.touchscreen.tap(x, y) if VIEWPORTS[vp_name].get("has_touch") and rng.random() < .5
             else page.mouse.click(x, y, click_count=rng.choice([1, 1, 1, 2, 3])))
        elif r < 0.40:  # click a random interactive element
            els = page.query_selector_all("a,button,summary,label,[role=button],input[type=checkbox],input[type=radio]")
            els = [e for e in els if e.is_visible()]
            if els:
                e = rng.choice(els)
                log.append("clickEl " + (e.get_attribute("id") or e.inner_text()[:30].replace("\n", " ")))
                e.click(timeout=1500, force=True)
        elif r < 0.55:  # type junk into a text field
            els = [e for e in page.query_selector_all("input:not([type=range]):not([type=checkbox]):not([type=radio]),textarea") if e.is_visible()]
            if els:
                e, s = rng.choice(els), rng.choice(JUNK)
                log.append(f"fill {e.get_attribute('id')} {s[:20]!r}")
                e.fill(s, timeout=1500) if rng.random() < .6 else (e.click(timeout=1500), page.keyboard.type(s[:200]))
        elif r < 0.68:  # abuse a slider
            els = [e for e in page.query_selector_all("input[type=range]") if e.is_visible()]
            if els:
                e = rng.choice(els)
                v = e.evaluate(f"""(el) => {{
                  const lo=+el.min||0, hi=+el.max||100, c={rng.random()};
                  const v = c<.2?lo : c<.4?hi : lo + (hi-lo)*c;
                  el.value=v; el.dispatchEvent(new Event('input',{{bubbles:true}}));
                  el.dispatchEvent(new Event('change',{{bubbles:true}})); return el.value; }}""")
                log.append(f"slider {e.get_attribute('id')}={v}")
        elif r < 0.74:  # random select option
            els = [e for e in page.query_selector_all("select") if e.is_visible()]
            if els:
                e = rng.choice(els)
                opts = e.evaluate("s => [...s.options].map(o => o.value)")
                if opts:
                    v = rng.choice(opts); log.append(f"select {e.get_attribute('id')}={v}")
                    e.select_option(v, timeout=1500)
        elif r < 0.84:
            k = rng.choice(KEYS); log.append("key " + k); page.keyboard.press(k)
        elif r < 0.93:
            dy = rng.choice([-1, 1]) * rng.randrange(100, 2500); log.append(f"scroll {dy}")
            page.mouse.wheel(0, dy)
        elif r < 0.96:
            nw, nh = rng.choice([(320, 568), (375, 740), (768, 1024), (1024, 700), (1440, 900), (1920, 1080)])
            log.append(f"resize {nw}x{nh}"); page.set_viewport_size({"width": nw, "height": nh})
        elif r < 0.98:
            log.append("lang toggle"); page.evaluate("document.getElementById('lang')?.click()")
        else:
            log.append("back/forward"); page.go_back(timeout=3000); page.go_forward(timeout=3000)

    for i in range(n_actions):
        try:
            act()
        except PWError as e:
            msg = str(e).split("\n")[0]
            if "Timeout" not in msg and "not attached" not in msg and "not visible" not in msg:
                add("driver", msg)
        page.wait_for_timeout(rng.choice([0, 20, 50, 120]))
        if not page.url.startswith(url.split("index.html")[0]):
            add("navigation", f"left page -> {page.url}")
            page.goto(url, wait_until="load")
        if i % 25 == 24 or i == n_actions - 1:
            W, H = page.viewport_size["width"], page.viewport_size["height"]
            try:
                c = checks(page)
            except PWError:
                continue
            bad = set(BAD_TEXT.findall(c["text"])) - baseline
            if bad:
                ctxs = [m.group(0) for m in re.finditer(r".{0,40}\b(NaN|Infinity|undefined)\b.{0,40}", c["text"])][:4]
                add("badtext", f"{sorted(bad)} :: {ctxs}")
            if c["overflowX"] > 1:
                add("overflowX", f"{c['overflowX']}px at {W}px wide; {c.get('offenders')}")

    shot = os.path.join(outdir, f"{vp_name}-seed{seed}.png")
    try:
        page.screenshot(path=shot)
    except PWError:
        shot = None
    browser.close()
    return {"viewport": vp_name, "seed": seed, "actions": n_actions, "issues": issues, "screenshot": shot}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--actions", type=int, default=300)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--viewports", default=",".join(VIEWPORTS))
    ap.add_argument("--out", default=os.path.join(ROOT, "tests", "monkey-out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    httpd, url = serve()
    results = []
    with sync_playwright() as pw:
        for vp in a.viewports.split(","):
            for s in map(int, a.seeds.split(",")):
                t = time.time()
                r = run(pw, url, vp, s, a.actions, a.out)
                r["secs"] = round(time.time() - t, 1)
                results.append(r)
                print(f"{vp:8} seed {s}: {len(r['issues'])} issue(s) in {r['secs']}s")
                for i in r["issues"]:
                    print(f"   [{i['kind']}] {i['msg'][:200]}")
    httpd.shutdown()
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
