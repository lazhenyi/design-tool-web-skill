#!/usr/bin/env python3
"""
QA for design-tool-web pages: screenshots + health checks + MOTION checks.

What it verifies
  health   console errors, horizontal overflow (incl. widened mobile layout viewport),
           content stuck hidden after scrolling the whole page, 3D canvas / fallback
  motion   (desktop, 3D disabled so software-GL cost doesn't pollute the numbers)
           * drag sync    - while an agent drags an element, the real DOM distance between the
                            cursor and the element's grab point (should be ~0px)
           * frame pacing - rAF intervals during build and during a wheel-scroll: p95 / max / count >25ms
           * gather       - at the bottom of the page every cursor is inside one tight cluster

Usage
  python3 preview.py path/to/index.html --out ./qa
  python3 preview.py index.html --out ./qa --three-local /path/to/three.min.js   # offline sandbox

Requires: pip install playwright && playwright install chromium
Exit code 1 when a hard check fails, else 0.
"""
import argparse
import json
import math
import pathlib
import sys

from playwright.sync_api import sync_playwright

PROFILES = [
    ("desktop", {"width": 1440, "height": 900}, {}),
    ("mobile", {"width": 390, "height": 844}, {"device_scale_factor": 2, "is_mobile": True, "has_touch": True}),
    ("reduced", {"width": 1280, "height": 800}, {"reduced_motion": "reduce"}),
]

FPS_JS = """
() => new Promise(res => {
  let n = 0; const t0 = performance.now();
  (function f(){ n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else res(n); })();
})
"""

STATE_JS = """
() => {
  const q = s => Array.from(document.querySelectorAll(s));
  const nodes = q('[data-node]');
  const cur = q('.cur').map(c => { const r = c.getBoundingClientRect(); return [r.left, r.top]; });
  let spread = 0;
  if (cur.length) {
    const cx = cur.reduce((s, p) => s + p[0], 0) / cur.length, cy = cur.reduce((s, p) => s + p[1], 0) / cur.length;
    spread = Math.max(...cur.map(p => Math.hypot(p[0] - cx, p[1] - cy)));
  }
  return {
    nodes: nodes.length,
    hiddenNodes: nodes.filter(n => getComputedStyle(n).opacity < 0.05).length,
    agents: cur.length,
    hasCanvas: !!document.querySelector('#hero3d canvas'),
    noWebgl: document.documentElement.classList.contains('no-webgl'),
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    layoutWiderThanVisual: Math.round(window.innerWidth - (window.visualViewport ? window.visualViewport.width : window.innerWidth)),
    gathered: document.body.classList.contains('gathered'),
    fixedClipped: [
      // content poking out of its own container (e.g. a toolbar button outside the pill)
      ...['#hud', 'header.top', 'header.top nav'].flatMap(sel => {
        const el = document.querySelector(sel);
        return (el && el.scrollWidth > el.clientWidth + 1) ? [sel + ' content wider than its box (' + el.scrollWidth + ' > ' + el.clientWidth + ')'] : [];
      }),
      // fixed UI cut off by the viewport
      ...['#hud', '#hud button', 'header.top .logo', 'header.top nav a'].flatMap(sel =>
        Array.from(document.querySelectorAll(sel)).filter(el => el.offsetWidth > 0).flatMap(el => {
          const r = el.getBoundingClientRect(), W = document.documentElement.clientWidth;
          return (r.right > W + 1 || r.left < -1) ? [sel + ' outside viewport (' + Math.round(r.left) + '..' + Math.round(r.right) + ' of ' + W + ')'] : [];
        })),
    ],
    clusterSpread: Math.round(spread),
  };
}
"""

# Installed before the page loads. Samples every animation frame.
SAMPLER_JS = """
(() => {
  window.__frames = []; window.__sync = {max: 0, n: 0}; window.__rec = false;
  let last = 0;
  (function loop(t) {
    if (window.__rec && last) window.__frames.push(t - last);
    last = t;
    const d = window.__dtw;
    if (d) {
      for (const a of d.agents) {
        const n = a.job;
        if (!n || n.state !== 'drag' || a.gk > 0.01) continue;
        const nr = n.el.getBoundingClientRect(), cr = a.el.getBoundingClientRect();
        const err = Math.hypot(cr.left - (nr.left + n.gx), cr.top - (nr.top + n.gy));
        window.__sync.n++; if (err > window.__sync.max) window.__sync.max = err;
      }
    }
    requestAnimationFrame(loop);
  })(0);
})();
"""


def pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(math.ceil(p * len(xs))) - 1)]


def scroll_through(page, out=None, name=None, step_frac=0.6, wait=1100):
    """Scroll the whole page in steps (elements are dragged in as they enter the viewport)."""
    vh = page.evaluate("innerHeight")
    shot_done = False
    y = 0
    while True:
        H = page.evaluate("document.documentElement.scrollHeight")
        if y + vh >= H - 2:
            break
        y = min(y + int(vh * step_frac), H - vh)
        page.evaluate(f"scrollTo(0,{y})")
        if out and not shot_done and y > vh * 0.9:
            page.wait_for_timeout(380)                     # catch agents mid-drag
            page.screenshot(path=str(out / f"{name}-04-scroll-building.png"))
            shot_done = True
            page.wait_for_timeout(max(0, wait - 380))
        else:
            page.wait_for_timeout(wait)


def run_profile(browser, html_url, out, name, viewport, ctx_kwargs, three_local):
    ctx = browser.new_context(viewport=viewport, **ctx_kwargs)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    if three_local:
        page.route("**/three.min.js", lambda r: r.fulfill(path=three_local, content_type="application/javascript"))

    page.goto(html_url, wait_until="load")
    page.wait_for_timeout(450)
    page.screenshot(path=str(out / f"{name}-01-hero-building.png"))
    page.wait_for_timeout(2800)
    page.screenshot(path=str(out / f"{name}-02-hero-settled.png"))
    fps = page.evaluate(FPS_JS)

    page.keyboard.press("d")                               # design view
    page.wait_for_timeout(350)
    page.screenshot(path=str(out / f"{name}-03-design-view.png"))
    page.keyboard.press("d")

    scroll_through(page, out, name)
    page.wait_for_timeout(3200)                            # let the cluster form
    state = page.evaluate(STATE_JS)
    page.screenshot(path=str(out / f"{name}-05-bottom-gathered.png"))
    ctx.close()
    state.update({"fps": fps, "errors": errors})
    return state


def run_motion(browser, html_url, out):
    """Desktop, 3D disabled: measures drag sync, frame pacing and the gather cluster."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.add_init_script(SAMPLER_JS)
    page.route("**/three.min.js", lambda r: r.abort())
    page.goto(html_url, wait_until="load")
    page.evaluate("window.__rec = true")
    page.wait_for_timeout(3200)                            # hero build
    build_frames = page.evaluate("window.__frames.splice(0)")

    # wheel scrolling, the way a person does it
    H = page.evaluate("document.documentElement.scrollHeight")
    vh = page.evaluate("innerHeight")
    page.mouse.move(700, 450)
    for _ in range(int((H - vh) / 70) + 6):
        page.mouse.wheel(0, 70)
        page.wait_for_timeout(28)
    scroll_frames = page.evaluate("window.__frames.splice(0)")
    page.wait_for_timeout(3200)
    state = page.evaluate(STATE_JS)
    sync = page.evaluate("window.__sync")
    page.screenshot(path=str(out / "motion-bottom-gathered.png"))
    ctx.close()

    def stats(fr):
        return {"frames": len(fr), "p95_ms": round(pct(fr, .95), 1), "max_ms": round(max(fr), 1) if fr else 0,
                "over25": sum(1 for x in fr if x > 25)}
    return {"build": stats(build_frames), "scroll": stats(scroll_frames), "dragSyncMaxPx": round(sync["max"], 2),
            "dragSamples": sync["n"], "gathered": state["gathered"], "clusterSpread": state["clusterSpread"],
            "hiddenNodes": state["hiddenNodes"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--out", default="./qa")
    ap.add_argument("--three-local", default=None, help="serve this file for **/three.min.js (offline testing)")
    args = ap.parse_args()

    html = pathlib.Path(args.html).resolve()
    if not html.exists():
        sys.exit(f"not found: {html}")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    report, failed = {}, False
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])

        for name, vp, kw in PROFILES:
            st = run_profile(browser, html.as_uri(), out, name, vp, kw, args.three_local)
            report[name] = st
            problems, warn = [], []
            if st["errors"]:
                problems.append(f"{len(st['errors'])} console error(s)")
            if st["overflowX"] > 1 or st["layoutWiderThanVisual"] > 1:
                problems.append(f"horizontal overflow {max(st['overflowX'], st['layoutWiderThanVisual'])}px "
                                "(clip the overflowing element; body overflow-x:hidden is not enough on mobile)")
            if st["hiddenNodes"]:
                problems.append(f"{st['hiddenNodes']} node(s) still hidden after scrolling the whole page")
            if st["fixedClipped"]:
                problems.append("fixed UI overflow: " + ", ".join(st["fixedClipped"]))
            if name != "reduced":
                if not st["gathered"]:
                    problems.append("agents did not gather at the bottom of the page")
                elif st["clusterSpread"] > 110:
                    warn.append(f"gather cluster loose (spread {st['clusterSpread']}px)")
            if not st["hasCanvas"] and not st["noWebgl"]:
                warn.append("no 3D canvas and no fallback class")
            if st["fps"] < 30 and name != "reduced":
                warn.append(f"fps {st['fps']} with software GL - not meaningful, see motion check")
            tag = "FAIL" if problems else ("WARN" if warn else "PASS")
            failed |= bool(problems)
            print(f"[{tag}] {name:8s} nodes={st['nodes']} agents={st['agents']} gathered={st['gathered']} "
                  f"spread={st['clusterSpread']}px canvas={st['hasCanvas']} " + "; ".join(problems + warn))
            for e in st["errors"][:5]:
                print("        ", e)

        m = run_motion(browser, html.as_uri(), out)
        report["motion"] = m
        problems, warn = [], []
        if m["dragSamples"] == 0:
            problems.append("no drag was observed (agents never carried an element)")
        elif m["dragSyncMaxPx"] > 3:
            problems.append(f"cursor drifts {m['dragSyncMaxPx']}px from the element it is dragging")
        if not m["gathered"]:
            problems.append("cluster did not form at the bottom")
        elif m["clusterSpread"] > 110:
            warn.append(f"cluster loose ({m['clusterSpread']}px)")
        if m["hiddenNodes"]:
            problems.append(f"{m['hiddenNodes']} node(s) still hidden")
        for k in ("build", "scroll"):
            share = m[k]["over25"] / max(1, m[k]["frames"])
            if share > 0.08 or m[k]["max_ms"] > 100:
                warn.append(f"{k}: {m[k]['over25']}/{m[k]['frames']} frames >25ms (max {m[k]['max_ms']}ms)")
        tag = "FAIL" if problems else ("WARN" if warn else "PASS")
        failed |= bool(problems)
        print(f"[{tag}] motion   dragSync={m['dragSyncMaxPx']}px ({m['dragSamples']} samples)  "
              f"build slow={m['build']['over25']}/{m['build']['frames']} max={m['build']['max_ms']}ms  "
              f"scroll slow={m['scroll']['over25']}/{m['scroll']['frames']} max={m['scroll']['max_ms']}ms  "
              f"cluster={m['clusterSpread']}px " + "; ".join(problems + warn))
        browser.close()

    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(f"\nscreenshots + report.json -> {out.resolve()}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
