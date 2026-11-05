# design-tool-web

Build web pages that look like they are **being assembled live by a team of AI agents**.

Each element on the page is grabbed and dragged into place by a colored cursor, with Figma-style selection boxes, corner handles and size labels trailing behind. When you scroll to the bottom, every cursor converges into a single cluster that reads `N agents online · all synced`. Dark single-page layout, Three.js hero, glitch slicing, scanline and scramble-decode transitions.

The project reverse-engineers that effect from a 21-second phone recording of a screen (source code was never visible). It ships a runnable single-file template, the mechanism docs, and an automated QA script. **Take the technique, not the original site's brand, copy, or project names.**

---

## What you see

| Layer | What happens | How it works |
|---|---|---|
| Content | Top bar / Hero / Work / Practice / Contact | Real semantic DOM; fully readable with JS disabled |
| Design layer | Blue hairline boxes, white handles, `W×H` labels | `getBoundingClientRect()` on the real DOM every frame, painted on an overlay |
| Agents | Named cursors (layout, type, motion, a11y…) with tags | claim → fly to spawn point → grab → drag home → release |
| Transitions | Horizontally sliced text, red scanline, scrambled characters resolving | `clip-path` slices + RGB split, WAAPI scanline, character decode |
| Hero | Blue torus knot with gold glowing nodes, slowly rotating | Procedural Three.js TorusKnot, no external models |
| HUD | Bottom capsule: agent dots, `N agents`, `N layers`, status, Design / Replay | Fixed; itself dragged in by an agent |

Two invariants separate "smooth" from "cheap":

1. **Real causality.** An element appears because a cursor grabbed it and dragged it there. Cursor position and element offset come from the same number, written in the same frame. Never "element fades in while a cursor drifts nearby".
2. **No dropped frames.** Animate only `transform` and `opacity`, never `filter: blur`. Keep the overlay in document space so cursors don't slide during scroll.

---

## Repository layout

```
.
├── SKILL.md                      # Method: workflow / architecture / parameters / pitfalls
├── README.md                     # This file
├── assets/starter/index.html     # Runnable single-file starter (all mechanics implemented)
├── references/
│   ├── agent-drag.md             # Core mechanics: orchestration, state machine, sync, coordinates, gather, parameters
│   ├── effects.md                # Effect recipes: selection engine, agent physics, glitch slicing, scramble, blueprint/terminal skins
│   ├── 3d-hero.md                # Swapping the hero: knot parameters, particle field, noise sphere, glTF, performance budget
│   ├── stack-and-scaling.md      # Path to multi-page / Vite / React Three Fiber
│   └── qa-checklist.md           # Pre-delivery checklist and budgets
└── scripts/preview.py            # Multi-profile screenshots + health checks + motion checks
```

---

## Getting started

### Option A: use it as an agent skill

Drop this directory into your agent's skills folder (for example `~/.claude/skills/design-tool-web/`, or wherever your harness looks), then describe the job:

> Build a portfolio single page where elements are dragged in by multiple cursors, the cursors converge at the bottom, dark cyber aesthetic.

The skill asks at most one clarifying question (brand, content, purpose), copies the starter, customizes it in order, and runs QA. Trigger phrases include: design-tool page, multi-cursor / agent swarm, Figma canvas, award or contest entry, glitch 3D landing page.

### Option B: edit the template directly

```bash
# Zero dependencies, zero build. Open in a browser.
cp assets/starter/index.html ./site/index.html
open ./site/index.html
```

Work on top of the template. Do not rewrite it from scratch. Responsive behavior, accessibility, progressive enhancement and failure fallbacks are already handled.

### Option C: verify before shipping

```bash
pip install playwright && playwright install chromium
python3 scripts/preview.py ./site/index.html --out /tmp/qa
```

The script scrolls through the whole page in three profiles (desktop 1440×900, mobile 390×844, reduced motion), takes screenshots, and prints one `PASS / WARN / FAIL` line per profile. A non-zero exit code means a hard check failed.

If the CDN is unreachable (sandbox, offline CI):

```bash
npm i three@0.128.0 --prefix /tmp/t3
python3 scripts/preview.py ./site/index.html --out /tmp/qa \
  --three-local /tmp/t3/node_modules/three/build/three.min.js
```

**Passing numbers do not mean it looks good.** Open at least four screenshots in `/tmp/qa`: an agent mid-drag, elements dragged in during scroll, the gathered cluster at the bottom, and one mobile view.

---

## Customization workflow

1. **Content and brand.** Replace headings, copy, nav, projects, `<title>` and description. Keep `data-node` on every element that should be circled; effects are switched on with attributes (table below).
2. **Agent roles.** Rename the tags in `CONFIG.agents` to roles that fit the project (`layout / type / motion / a11y / perf / copy`). These are part of the story, not decoration.
3. **3D hero.** Default is a blue torus knot with six gold nodes. See `references/3d-hero.md` to change the form.
4. **Pacing.** Tune `claimGap`, `fly` / `drag`, `spawn`, `linger`, `gatherSpacing`.
5. **Extra effects.** Click-to-select with an inspector, blueprint/terminal/light skins, drag handle animation: see `references/effects.md`.

### Data attributes

| Attribute | Purpose |
|---|---|
| `data-node` | Element is measured and dragged in by an agent. Only add it to elements you want circled (keep active boxes ≤ 40) |
| `data-build` | Marks a screen (section) for build pacing statistics |
| `data-glitch` | Title glitch slicing, fired once on landing, ~560ms, never looping |
| `data-scramble` | Scramble-decode for mono labels, fired on landing |
| `data-count="2019"` | Count-up number; `data-dec="1"` for decimals, `data-suffix="%"` for a suffix |
| `data-gather` | The convergence stage at the end of the page. A static element that fades in with gather progress; it is not dragged |

### CONFIG knobs

```js
const CONFIG = {
  agents: [...],                   // tag + color; order = priority on small screens (first agentsSmall win)
  agentsSmall: 7,                  // cursor count below 720px (desktop uses all 12)
  claimGap: 70,                    // ms between claims; the "relay" rhythm
  fly:   {speed: 1.5, min: 340, max: 880},  // flight to spawn point: px/ms, clamped to [min,max] ms
  drag:  {hold: 90, min: 620, max: 980},    // pause after grab, then drag duration range
  spawn: {desktop: [150, 300], small: [70, 140]}, // spawn distance from final position (px)
  linger: 450,                     // how long the box stays after release
  wander: [900, 1900], dwell: [250, 900],  // idle wandering / dwelling
  gatherSpacing: 15,               // spacing between cursors in the final cluster (px)
  scanMs: 900                      // duration of one scanline sweep
};
```

Common adjustments:

| Goal | Knob |
|---|---|
| Feel more simultaneous | Lower `claimGap` (30–50ms) |
| Feel more sequential | Raise `claimGap` (120–200ms) |
| Snappier drags | Lower `drag.max` toward 800; below ~500 it reads as teleporting |
| Elements fly farther | Raise `spawn.desktop` toward 360; watch for horizontal overflow |
| Looser cluster | Raise `gatherSpacing` to 20–24 |
| Calmer mobile | Lower `agentsSmall` to 5 |

Built-in shortcuts: `D` toggles Design view (all boxes stay visible), `R` replays the whole build.

---

## Architecture: document-space overlay, one pipeline per frame

```
z 60  #dl / #dlf   Overlay: selection boxes (.sel) + agent cursors (.cur)   pointer-events:none
                   #dl  = absolute, document coordinates (scrolls with the page, compositor-synced)
                   #dlf = fixed, only for fixed nodes (top bar / HUD)
z 50  #hud         Bottom toolbar (itself a dragged-in node)
z 45  #scan        Red scanline (WAAPI, one shot)
z  0  Content      Real DOM; elements with data-node are measured and dragged in
z -1  .hero-3d     Three.js canvas (inside #hero's stacking context, behind the text)
End   [data-gather] Convergence stage
```

One `requestAnimationFrame` loop, with reads and writes strictly separated:

1. **Read.** Read every node's `getBoundingClientRect()` once, subtract the offset we applied, and you have the "final layout position".
2. **Queue.** `hidden` nodes entering the viewport are queued; when gather progress `G > 0.6`, everything left in the queue is revealed instantly.
3. **Progress → offset.** `T = D × (1 − ease(p))`.
4. **Agents.** Idle cursors claim work every `claimGap`; a dragging cursor equals its element's grab point; the rest fly or wander on time-based easing; finally each is blended toward its cluster slot by `gk`.
5. **Write.** Element `transform`, selection boxes, cursors, stage opacity, HUD state. Only the overlay and dragged elements are touched.
6. **3D.** Rendered only while the hero is visible and the tab is active.

The key insight: **the overlay is not a pre-rendered animation or screenshot, it is measured from the real DOM every frame.** That is why responsiveness, accessibility, SEO and copy edits survive the effects. It is what makes a page like this both flashy and usable.

Details (state machine, why document space is mandatory, spawn filtering, gather math): `references/agent-drag.md`.

---

## What the QA script checks

`scripts/preview.py` reports two groups.

**Health checks** (all three profiles scroll the full page):

| Check | Level | Meaning |
|---|---|---|
| Console errors / page exceptions | FAIL | Any `console.error` or uncaught exception |
| Horizontal overflow | FAIL | `scrollWidth − clientWidth > 1`, or layout viewport wider than visual viewport (catches a widened mobile layout viewport) |
| Fixed UI overflow | FAIL | Top bar / HUD content wider than its own container, or outside the viewport |
| Content stuck hidden | FAIL | Any `[data-node]` still at opacity ≈ 0 after scrolling everything |
| No gather at the bottom | FAIL | `<body>` never gets `.gathered` (reduced motion excepted) |
| Loose cluster | WARN | Farthest cursor > 110px from the cluster center |
| No 3D and no fallback | WARN | Neither a canvas nor `.no-webgl` is present |

**Motion checks** (desktop, **3D disabled**, so software rendering does not pollute the numbers):

| Check | Level | Meaning |
|---|---|---|
| Drag sync | FAIL (> 3px) | Max real DOM distance between a dragging cursor and its element's grab point. Template measures 0.07px, including during wheel scrolling |
| No drag observed | FAIL | Agents never actually carried anything |
| Slow frame share | WARN (> 8% or max > 100ms) | Frames over 25ms, counted separately for build and for wheel scroll |
| Cluster forms | FAIL | Cursors converge at the bottom |

The script does not use p95: frame intervals are quantized (16.7 / 33.3ms), so a single stutter doubles p95. Read the slow-frame share and the maximum instead, and re-check on real hardware. Low fps under software rendering is expected. **Do not cut effects because of it**; measure the overlay alone with 3D removed (the template sits around 60fps there).

---

## Pitfalls (all hit for real)

**Motion and sync**

- Entry animations using `filter: blur` are the usual cause of jank. Use `transform` / `opacity` only.
- A `position: fixed` overlay makes cursors lag by one frame of scroll: the page moves on the compositor thread while cursors update on the main thread. Measured drift was 70px; document space brings it to 0.07px.
- Sending queued cursors off to wander made the first screen take 3.5s (2.0s after the fix). Queued cursors must wait in place, and wandering must be interruptible by new work.
- CSS `transform` on a node is overwritten by JS. Center with `margin:auto` / `inset`, not `translate(-50%,-50%)`.
- A spawn point outside the viewport widens the mobile layout viewport; one below the document bottom makes the page taller. The template filters spawn candidates four ways.
- Cursors still easing out of the cluster (`gk > 0.02`) must not claim work, and `gk` is forced to 0 while dragging, otherwise the cluster pulls them off target.

**Layout and rendering**

- Full-width selection boxes: block elements stretch inside a flex column. Use `width:fit-content` on headings and `align-self:flex-start` on `section > [data-node]`.
- A negative `right` on the mobile 3D canvas causes horizontal overflow **and widens `innerWidth`**, pushing fixed elements off screen. `body{overflow-x:hidden}` does not stop it; use `overflow-x:clip` on the overflowing container, and detect with `scrollWidth - clientWidth`.
- 3D covering the text: add `isolation:isolate` to `#hero` and `z-index:-1` to the canvas. Do not use negative z-index on body-level elements.
- Invisible gold nodes: the node radius must exceed the tube radius (template: .27 > .2), and the glow needs `AdditiveBlending`.
- Interleaved reads and writes force repeated layout. Read all rects first, then write styles.
- Any JS error can leave `opacity:0` content invisible forever. Keep the `.reveal-all` 5-second fallback, and only fire it if the main loop never started.

Ten more mechanism pitfalls and fifteen engineering ones are in `SKILL.md` §6 and `references/agent-drag.md` §10.

---

## Manual pass before delivery

The script cannot judge taste, feel, real-device performance or contrast. At minimum confirm:

- [ ] Content is complete and readable with JS disabled
- [ ] No more than three effect types running in one screen; the scanline fires once per screen change, never in a loop
- [ ] Under `prefers-reduced-motion`: no cursors, no scanline, no glitch, static 3D, content shown directly
- [ ] Mobile drops to 5–7 agents, 3D sits behind the text, HUD is narrower
- [ ] Every effect has a narrative reason; delete the ones that don't
- [ ] Re-checked smoothness on a real phone with a real GPU
- [ ] Brand, copy and project names fully replaced, nothing carried over from the original site

Full checklist in `references/qa-checklist.md`.

---

## Stack and scaling path

- **Default:** single-file vanilla JS + Three.js (r128, pinned on cdnjs). No build, publishable as-is, good enough for contest-grade single pages.
- **Upgrade to Vite / Next + React Three Fiber + GSAP** when there is more than one page, when you need routing and a CMS, or when the 3D scene gets complex. The overlay algorithm is framework-agnostic (attribute nodes, measure per frame). Migration notes in `references/stack-and-scaling.md`.
- Do not add a framework for prestige. The bottleneck for pages like this is pacing and taste, not engineering effort.
- When publishing as a shareable page, scripts may only come from `cdnjs.cloudflare.com` with pinned versions. Do not use `window.storage` or `api.anthropic.com`.

---

## Scope

**Good fit:** portfolios, studio or product landing pages, contest and award submissions, creative single pages, "web design can do this?" showcases.

**Poor fit:** dashboards, forms and data-dense interfaces; multi-page sites that need SEO and content operations (possible, but migrate first per `stack-and-scaling.md`); and anything that requires copying someone else's brand or assets.

---

## Credit and boundaries

The method and its numbers come from observing a public screen recording and reconstructing it through engineering; the source was never visible. The starter ships with demo copy (ZhenYi's personal site) so the page is never empty; replace it with your own brand and content. **Take the technique, not someone else's brand names, copy, images or project content.**

The repository currently has no license file. Add one before publishing or redistributing.
