# Pre-delivery self-check (qa-checklist)

Run the script first, then look at the screenshots, then walk the manual list. The script only catches things **a machine can judge**; taste, feel, real-device performance and contrast are not among them.

## Contents
1. Run `preview.py`
2. What to look for in the screenshots
3. What the script cannot check and a human must
4. Budgets
5. Accessibility
6. Flash safety
7. Common failures and where to look

---

## 1. Run `preview.py`

```bash
python3 scripts/preview.py <index.html> --out /tmp/qa
# when the sandbox cannot reach the CDN:
npm i three@0.128.0 --prefix /tmp/t3
python3 scripts/preview.py <index.html> --out /tmp/qa --three-local /tmp/t3/node_modules/three/build/three.min.js
```

It prints one `PASS / WARN / FAIL` line per profile. The first three lines are **health checks**; the fourth, `motion`, is the **motion check**.

**Health checks** (desktop 1440×900, mobile 390×844, reduced motion; every profile **scrolls through the whole page** step by step, because elements are only dragged in when they enter the viewport):

| Check | Level | Meaning |
|---|---|---|
| Console errors / page exceptions | FAIL | Any `console.error` or uncaught exception. A failed CDN lookup in a sandbox also counts; distinguish environment from code |
| Horizontal overflow | FAIL | `scrollWidth − clientWidth > 1`, or the layout viewport wider than the visual viewport. The latter specifically catches a widened mobile layout viewport |
| Fixed UI overflow | FAIL | Top bar / HUD content wider than its own container (a button poking out of the pill), or outside the viewport |
| Content stuck hidden | FAIL | After scrolling the whole page, some `[data-node]` still has opacity near 0 |
| No gather at the bottom | FAIL | After scrolling to the bottom and waiting, `<body>` lacks `.gathered` (reduced motion excepted) |
| Loose cluster | WARN | Farthest cursor > 110px from the cluster center |
| No 3D canvas and no fallback class | WARN | 3D neither appeared nor triggered the `.no-webgl` fallback |

**Motion check** (desktop, **3D off**, so software-rendered WebGL does not pollute the numbers):

| Check | Level | Meaning |
|---|---|---|
| Drag sync | FAIL (>3px) | Max real DOM distance between cursor and element grab point during a drag. The template measures 0.07px, including during wheel scrolling |
| No drag observed | FAIL | An agent never actually carried an element |
| Slow frame share | WARN (>8% or max >100ms) | Frames over 25ms, counted separately for the build phase and for wheel scrolling |
| Cluster forms | FAIL | Same as above |

**Why not p95**: frame intervals are quantized (16.7ms or 33.3ms), so a single stutter doubles p95 and the same code bounces between two values across runs. The slow-frame share and the maximum are steadier. In a sandbox the slow-frame share usually sits at a few percent, **which cannot distinguish environment noise from a real regression**: run it a few times before and after a change, and verify on real hardware.

The script screenshots all three profiles, named `<profile>-NN-<stage>.png`; the motion check saves `motion-bottom-gathered.png` separately.

## 2. What to look for in the screenshots

Look at at least these:
- `desktop-01-hero-building`: about 0.45s after load. You should see **dashed ghost boxes** at each element's spawn point, cursors flying in from the screen edges, and the red scanline sweeping past; most of the page is still empty.
- `desktop-04-scroll-building`: while scrolling. Some element should be **held by a cursor** (solid box + handles + size label + name tag), with dashed ghost boxes where body copy has not arrived yet.
- `desktop-03-design-view`: Design view. Every settled element's box is lit, and **boxes hug the text** instead of spanning the row.
- `desktop-05-bottom-gathered` and `mobile-05-bottom-gathered`: at the bottom. Cursors clumped in the middle of the stage frame, the caption reads "N agents online · all synced", HUD state is `synced`; on mobile the HUD is complete and not cut off.
- `mobile-02-hero-settled`: mobile steady state. Full nav, 3D behind the text and not obscuring it.

All-green numbers with an ugly result is a common outcome. Trust the picture.

## 3. What the script cannot check and a human must

- **Real-device smoothness**: scroll through it on a mid-range phone and on a laptop. Software-rendered frame rates mean nothing.
- **Keyboard**: Tab reaches nav, buttons and inputs in order; the focus ring is clearly visible (the template uses a 2px blue outline).
- **Screen readers**: with CSS off the reading order still makes sense; the overlay and the 3D canvas are `aria-hidden` and are not announced; scramble decode writes `textContent` directly and lasts only ~650ms, after which the final text is back. The template adds no extra protection here, so a screen reader reading that label during those 650ms will announce gibberish. It is a known small gap; labels are short, so the impact is limited, but if screen-reader users matter, enable `data-scramble` only on non-essential labels.
- **Contrast**: body copy against the background, and the mono micro-labels (11px gold) against it. Small gold text on dark usually works, but re-check after changing skins.
- **JS off**: with scripts disabled the content is complete and readable (the `.js` class is added by an inline script, so without scripts nothing is hidden).
- **Reduced motion**: with it on system-wide, no cursors, no scanline, no glitch, static 3D (the `reduced` profile screenshots this, but confirm by eye).
- **Resize / rotate**: drag the window width; boxes should track in real time with no misplaced remnants.
- **Replay / Design / shortcuts**: `R` replays, `D` toggles Design view, and neither fires while typing in an input.

## 4. Budgets

| Item | Budget | Note |
|---|---|---|
| Simultaneous boxes | ≤ 40 | One rect read per circled element per frame |
| Agent cursors | ≤ 12 desktop, ≤ 7 mobile | More is just noise |
| 3D | < 100k triangles, < 50 draw calls, pixel ratio ≤ 2 | See `3d-hero.md` |
| Single-file size | < 16MB (publish limit); realistically far below 1MB | Inlined images balloon fast |
| First screen text | Must not depend on 3D loading | A failed 3D script must not block content |
| Layout shift | 0 | Reveal animation touches only `opacity / transform / filter`, never size |

Run Lighthouse if you can. A 3D page rarely scores perfectly on mobile; do not cut the hero for the score. Accessibility, however, should stay high, and that is achievable.

## 5. Accessibility

- Content uses real semantic tags (`h1/h2/p/a/button/form`); effects are only an overlay.
- The overlay and the decorative 3D canvas: `aria-hidden="true"` and `pointer-events:none`.
- The HUD is `role="toolbar"` with readable button labels and `aria-pressed`.
- Every interactive element has a visible focus style.
- `prefers-reduced-motion` is respected (see `effects.md` section 10).

## 6. Flash safety

Glitch slicing switches position rapidly during a ~0.56s burst, so be deliberate about it:
- Each element **fires once**; it never loops and never re-fires on scroll.
- Apply it only to local text. **Do not** alternate high-contrast light/dark over large areas (this can trigger photosensitive discomfort).
- Keep the number of elements glitching at the same time low; the template claims nodes one at a time with `claimGap` spacing, so they do not burst together.
- Respect reduced motion, and consider adding a "turn effects off" switch in the HUD for visitors who need it.

I have not run formal flash-compliance measurement on the glitch effect. For contexts with hard compliance requirements (government, education, healthcare), have a qualified specialist measure it to the relevant standard.

## 7. Common failures and where to look

| Symptom | Likely cause | Fix |
|---|---|---|
| Top bar / HUD pushed off-screen on mobile | Some element overflows horizontally and widens the layout viewport | `overflow-x:clip` on the container where the overflow originates; `body{overflow-x:hidden}` does not work |
| Selection box is a full-width strip | Block element stretched by flex | `width:fit-content` + `align-self:flex-start` |
| Gold nodes missing | Node sphere radius ≤ tube radius | Node radius > `tube` |
| Halo looks brown | Normal alpha blending | Use `AdditiveBlending` |
| 3D covers the text | Absolutely positioned canvas paints above static text | `#hero{isolation:isolate}` + canvas `z-index:-1` |
| Numbers do not count | `data-count` on a child, while `reveal` only handles the node itself | Handle descendants in `reveal` (already fixed in the template) |
| Content never appears | A JS error interrupted the reveal | Keep the `.reveal-all` fallback; check the console |
| Box width jumps during scramble | Used on a proportional font | Scramble-decode only on mono text |
| Cursor "slides" across the element | Overlay is `position:fixed`, so scrolling runs on the compositor while cursors update on the main thread | Put the overlay in document space (`position:absolute` + `scrollY`), see `agent-drag.md` section 5 |
| First screen builds slowly | Queued cursors were sent wandering, or wandering cannot be interrupted | Wait in place when queued; mark wander segments `idle` and make them interruptible |
| Cursor drifts at the start of a drag | A cursor just released from the cluster (`gk>0`) claimed the job | Require `gk<0.02` before claiming; force `gk=0` while dragging |
| Page gets wider/taller during drag-in | Spawn point puts the element off-screen horizontally or below the document bottom | Filter spawn candidates (see `agent-drag.md` section 6) |
| HUD button pokes out of the pill | Content added but mobile was not narrowed | Hide secondary items on small screens (dots, layer count) |
