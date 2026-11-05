---
name: design-tool-web
description: A complete method and runnable template for building immersive "design-tool style" web pages that expose their own design file as they render — Figma-style blue boxes with handles and size labels, every element dragged into place by an "AI agent" cursor, all cursors converging at the bottom, glitch and scramble transitions, a Three.js hero, and an agents/layers toolbar. Build design-tool, Figma-canvas or multiplayer-cursor sites for portfolios, studio sites, award entries and contest pages. Use whenever a request mentions this kind of page, multi-cursor or agent swarms, award or contest web pages, portfolios, selection boxes and multiple cursors, cyber or glitch 3D landing pages, "web design can do this?", or a screen recording of such a page, even without the words skill or design tool. Not for dashboards or forms, and not for copying another brand's copy or assets.
---

# Design-tool web pages (design-tool-web)

A method for making a web page reveal the design tool while it is still being rendered: **every element on the page is grabbed and dragged into place by an agent cursor** (with a selection box, handles and a size label), and once the drag is done the box leaves. Scroll to the bottom and **all agent cursors converge into a single cluster**. What the visitor sees is "this page was assembled on the spot by a team of AI colleagues".

Two properties must hold. They decide whether it looks smooth or cheap:

1. **Real causality.** An element appears because a cursor grabbed it and dragged it there. Cursor position and element offset come from the same number, computed in the same frame. Never "element fades in while a cursor drifts nearby".
2. **No dropped frames.** Animate only `transform` and `opacity`, never `filter: blur`. Keep the overlay in document space, so cursors do not slide during scroll.

**Deliverable:** one runnable single-file site (start from `assets/starter/index.html`), adapted to the user's brand and content, passing the self-check in `scripts/preview.py`.

## 0. First, what this page is doing

This skill was reverse-engineered from a 21-second phone recording of a screen. The source code was never visible. The table separates "what is visible in the recording" from "my inference", so you do not replicate an inference as if it were fact.

| Layer | Visible in the recording | Approach (this skill) |
|---|---|---|
| Content | Dark single-page site: top nav, huge hero headline "Systems that hold up.", stats, project list, contact | Real semantic DOM, dark, tight-tracking bold headings and mono micro-labels |
| Design layer | Thin blue selection outline, four white corner handles, `width × height` label hugging the element, faint blue fill | Measure the real DOM with `getBoundingClientRect()` every frame, paint boxes on a fixed overlay |
| Agents | A crowd of small arrow cursors in different colors, scattered and moving, some with name tags | Each cursor claims one element: fly to spawn point → grab → drag home → release (see `references/agent-drag.md`) |
| Transitions | Text sliced horizontally and offset (pixel tearing), a red vertical line sweeping across, characters scrambling then resolving | `clip-path` slices plus RGB split, a WAAPI scanline, character scramble-decode |
| Hero | A blue interlaced knot with a gold glowing node, slowly rotating | Procedural Three.js TorusKnot plus gold nodes; no external model |
| HUD | Bottom toolbar: colored dots, "N agents", "layers", buttons (resolution too low to read; the exact copy is a guess) | Fixed capsule: agent count, layer count, Design view toggle, Replay |

Key insight: **the overlay is not a pre-made animation or screenshot. It is measured from the real DOM every frame.** That is why responsiveness, accessibility, SEO and copy edits survive the effects. It is what lets a page like this be both flashy and usable.

## 1. Workflow

### Step 1 · Establish the brief (ask at most one question)
You need to know: the brand or topic, how many screens the content has, and the purpose (contest, portfolio, client site). If the user did not say, do not interrogate them. Build with the defaults below and state the assumption in one line of your reply:
- Theme: the demo copy already in the template (a Rust engineer's personal site). Dark.
- 4 screens: Hero → Work (3 projects) → Practice (3 columns) → Contact
- Accent: blue `#2f6bff`, gold `#ffb62e`, scanline red `#ff3b30`

Do not reuse the brand names, copy or project names from the recording. The template ships with demo content so the page is never empty; replace it with the user's own.

### Step 2 · Copy the starter
```bash
mkdir -p /mnt/user-data/outputs/site && cp <skill>/assets/starter/index.html /mnt/user-data/outputs/site/index.html
```
The template already contains every mechanism and has been verified. **Edit it; do not rewrite it from scratch.**

### Step 3 · Customize, in this order
1. **Content and brand.** Replace headline, copy, nav, projects. Keep `data-node` on every element that should be circled. Switch effects on with attributes: `data-glitch` (headline glitch slices), `data-scramble` (mono label scramble-decode), `data-count` (count-up, optionally `data-dec`, `data-suffix`).
2. **Agent names.** Change the tags in `CONFIG.agents` to roles that fit the project (layout / type / motion / a11y / perf). This is part of the narrative, not decoration.
3. **3D hero.** Default is a blue interlaced knot with 6 gold nodes. To change the form, read `references/3d-hero.md`.
4. **Pacing.** Tune `CONFIG.claimGap` (relay interval), `fly` / `drag` (flight and drag durations), `spawn` (spawn distance), `linger` (how long the box stays), `gatherSpacing` (cluster tightness). See section 3 and `references/agent-drag.md`.
5. **Extras** (click-to-select, blueprint or terminal skin, drag-handle animation): read `references/effects.md`.

### Step 4 · Self-check (mandatory)
```bash
python3 <skill>/scripts/preview.py /mnt/user-data/outputs/site/index.html --out /tmp/qa
```
It screenshots and checks desktop, mobile and reduced-motion profiles for: console errors, horizontal overflow, fixed UI overflow or off-screen, content stuck hidden, cluster formation at the bottom, and 3D presence. It also runs a **motion check** (desktop, 3D off): the real drift between cursor and element grab point during a drag (should be ~0px), frame intervals and slow-frame share, and how tightly the cluster gathers. Then **look at the screenshots** — at minimum `*-01-hero-building` (a cursor mid-drag), `*-04-scroll-building` (drag-in during scroll), `*-05-bottom-gathered` (gathered at the bottom) and one mobile shot. Numbers passing does not mean it looks good.

If the sandbox cannot reach the CDN, `npm i three@0.128.0` and add `--three-local node_modules/three/build/three.min.js`. Low fps under software-rendered WebGL is normal; do not cut effects because of it. To judge the overlay's own cost, measure with 3D removed (the template is around 60fps in that case).

### Step 5 · Deliver
- If the user wants files: put them in `/mnt/user-data/outputs/` and call `present_files`.
- To publish a shareable page in the conversation (when an Artifact tool is available): the single HTML file is enough. Scripts may only come from `cdnjs.cloudflare.com` with pinned versions (the template already complies). Do not use `window.storage` or `api.anthropic.com`.
- In your reply cover three things: what you built, what you assumed, and which knobs exist. Do not paste the whole source.

## 2. Architecture: document-space overlay, one pipeline per frame

```
z 60  #dl / #dlf   Overlay: selection boxes (.sel) + agent cursors (.cur)   pointer-events:none
                   #dl  = position:absolute, document coordinates (scrolls with the page, compositor-synced)
                   #dlf = position:fixed, only for fixed nodes (top bar / HUD)
z 50  #hud         Bottom toolbar (itself a dragged-in node)
z 45  #scan        Red scanline (WAAPI, one shot)
z  0  Content      Real DOM; elements with data-node are measured and dragged in
z -1  .hero-3d     Three.js canvas (inside #hero's own stacking context, behind the text)
End   [data-gather] Stage where cursors converge (static element, fades in with gather progress)
```

There is a single `requestAnimationFrame` loop:

1. **Read phase.** Read every node's `getBoundingClientRect()` once, and **subtract the offset we applied ourselves** to get the "final layout position".
2. **Queue.** `hidden` nodes entering the viewport are queued; at the bottom (`G>0.6`) whatever is left in the queue is revealed immediately.
3. **Drag progress → offset `T`.** `T = D × (1 − ease(p))`.
4. **Agents.** Idle cursors claim the next element (round-robin, `claimGap` apart); a dragging cursor equals the element's grab point; the rest fly or wander on time-based easing; finally each is blended toward its cluster slot by the gather factor `gk`.
5. **Write phase.** Element `transform`, boxes, cursors, stage opacity, HUD state (write only the overlay and the dragged element; keep reads and writes separate to avoid layout thrash).
6. **3D.** Render only while the hero is visible and the tab is active.

Full mechanics, why the coordinate system must be document space, and how gather progress is computed: `references/agent-drag.md`.

## 3. Key parameters

The full table is in `references/agent-drag.md` section 8. The ones you will touch most:

| Parameter | Default | Guidance |
|---|---|---|
| `claimGap` | 70ms | Interval between claims. Smaller reads as simultaneous grabbing, larger as sequential construction |
| `fly.speed / min / max` | 1.5px/ms, 340–880ms | How fast a cursor flies to its spawn point |
| `drag.min / max` | 620–980ms | Drag duration; too short reads as teleporting, too long drags |
| `spawn.desktop / small` | 150–300 / 70–140px | How far from its final position an element starts |
| Cursor count | 12 desktop / 7 mobile | Measured: the first screen (11 elements) builds in ~2.0s desktop, ~2.2s mobile. More is just noise |
| `gatherSpacing` | 15px | Cluster tightness |
| Active boxes | ≤ 40 | One rect read per circled element per frame; only put `data-node` on elements you want to show |
| Glitch duration | ≈560ms | Fires once per element, never loops; only on local text, never large-area high-contrast flashing (see the flash-safety section of `references/qa-checklist.md`) |
| Accents | blue / gold / red | Change the tokens in `:root`; agent colors live in `CONFIG.agents` |

## 4. Choosing a stack

- **Default: single-file vanilla JS + Three.js (cdnjs, r128).** No build step, publishable as-is, good enough for a contest-grade single page.
- **Upgrade to Vite / Next + React Three Fiber + GSAP** when there is more than one page, when you need routing and a CMS, or when the 3D scene is complex. The overlay algorithm is framework-agnostic (attribute the nodes, measure every frame). Migration notes in `references/stack-and-scaling.md`.
- Do not add a framework for the sake of sophistication. The bottleneck for this kind of page is pacing and taste, not engineering effort.

## 5. Making a page that wins: the quality bar

1. **Content before effects.** With JS off, the content is still complete and readable (handled by the template's `.js` progressive enhancement and the 7-second fallback reveal).
2. **Effects carry a story.** Agent tags, selection boxes and the scanline all say one thing: the page is being built. If an effect cannot justify itself, delete it.
3. **Restraint.** No more than three kinds of motion on screen at once. The scanline fires once per screen change; it never loops.
4. **Reduced motion.** Under `prefers-reduced-motion`: no cursors, no scanline, no glitch, static 3D frame, content shown immediately (already implemented).
5. **Mobile.** Fewer agents, 3D behind the text, narrower HUD (already implemented).
6. **Real-device check.** Even after screenshots pass, watch it once on a real phone with a real GPU.

## 6. Common pitfalls (most were actually hit while building this template)

**Motion and sync** (these matter most for smoothness):
- **Using `filter: blur` for entrances.** This is the usual cause of jank. Animate `transform` and `opacity` only.
- **Cursors "sliding" across elements.** If the overlay is `position:fixed`, scrolling happens on the compositor thread while cursors update on the main thread, so cursors lag by one frame of scroll (measured up to 70px while scrolling and dragging). The overlay must live in document space (`position:absolute` plus `scrollY`); measured drift drops to 0.07px.
- **Queued cursors sent off to wander.** Only one cursor may pass the claim gate per frame; the rest must wait in place, not wander. Otherwise the first screen takes 3.5s+ to build (2.0s after the fix). Wandering must also be interruptible by new work.
- **Element offset using CSS `transform` for centering.** It gets overwritten by JS. Center with `margin:auto` / `inset` instead (the 3D container and the HUD were changed for this reason).
- **Drag causing overflow.** The spawn point must not take the element off-screen horizontally (this widens the mobile layout viewport), nor below the bottom of the document (this makes the page taller).
- **Cursors that just left the cluster drifting on claim.** A cursor with `gk>0` gets pulled by the cluster after claiming. Require `gk<0.02` before claiming and force `gk=0` while dragging.
- **Judging smoothness with p95.** Frame intervals are quantized (16.7/33.3ms); one stutter doubles p95. Look at the slow-frame share and the maximum, and verify on a real device.

**Layout and rendering**:
- **Selection box spanning a whole row.** Block elements stretch inside a flex column, so the box becomes a full-width strip. Add `width:fit-content` to headings and `align-self:flex-start` to `section > [data-node]` so the box hugs the text.
- **Mobile nav pushed off-screen.** A negative `right` on the 3D canvas overflows horizontally and **widens the mobile layout viewport** (`innerWidth` grows and fixed elements follow it off-screen). `body{overflow-x:hidden}` does not stop this. Use `overflow-x:clip` on the container where the overflow originates. Detect with `scrollWidth - clientWidth`, **not** `innerWidth`, which is itself inflated (the preview script implements this and has been verified).
- **Gold nodes invisible.** The node sphere radius must exceed the tube radius (template: sphere .27 > tube .2), otherwise it is swallowed by the tube. The glow needs additive blending (`AdditiveBlending`); normal alpha blending looks dull and brown.
- **3D covering the text.** An absolutely positioned canvas paints above static text by default. Add `isolation:isolate` to `#hero` and `z-index:-1` to the canvas. Do not put a negative z-index on a body-level element; it drops behind the body background.
- **Numbers not counting.** With `data-count` on a child element, `reveal()` only handling the node itself misses it. The template now handles descendants too.
- **Content never appearing.** Any JS error can leave `opacity:0` content invisible forever. Keep the `.reveal-all` fallback.
- **Interleaved reads and writes.** Calling `getBoundingClientRect()` inside a loop that also writes styles forces repeated layout. Read everything first, then write.
- **Low fps under software GL ≠ a slow page.** Measure again with 3D removed before cutting effects.
- **The QA script has blind spots too.** In this template the fixed-UI overflow check took three revisions before it caught the real problem (first it looked for viewport overflow, then it turned out a button was poking out of its own pill container). Whenever you add a check, verify it against a deliberately broken build.
- **Scope of copying.** Learn the effect and the technique; do not copy someone's brand names, copy, images or project content.

## 7. Reference files (read as needed)

- `references/agent-drag.md` — **Core mechanics**: drag orchestration, cursor state machine, sync principles, document-space overlay, bottom gather, parameter table, variants and pitfalls. Read this first.
- `references/effects.md` — Full recipes and variants for every effect: selection engine, agent physics, glitch slicing (single and multi-layer), scramble decode, scanline and rulers, click-to-select with an inspector, blueprint/terminal/light skins, orchestration timeline. Read when adding effects or changing the style.
- `references/3d-hero.md` — Changing the hero: knot parameters, particle field, noise sphere, loading glTF, performance budget, degradation. Read when changing the 3D form.
- `references/stack-and-scaling.md` — Path to multi-page / frameworks / React Three Fiber, plus version pinning and CSP constraints.
- `references/qa-checklist.md` — Self-check list: performance budget, accessibility, flash safety, mobile, what to look for in screenshots. Read before delivering.
- `scripts/preview.py` — Multi-profile screenshots and health checks.
- `assets/starter/index.html` — Runnable starter template.
