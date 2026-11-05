# Effect recipes (effects)

The snippets use the starter template's names: `nodes` (each node has `fr` final layout rect, `T` current offset, `state`, `until`), `agents`, `CONFIG`, `reveal(n)`, `pulse(a)`, `dl` (document-space overlay), `dlf` (viewport-space overlay). They paste straight into the template's IIFE. **The drag orchestration and gather mechanics themselves live in `agent-drag.md`**; this file only covers effects layered on top.

## Contents
1. Selection engine: principle and extensions
2. Agent cursors: physics and "personality"
3. Glitch slicing: single and multi-layer
4. Scramble decode and count-up
5. Scanline, rulers and coordinate readout
6. Click-to-select: letting visitors "circle" elements too
7. Drag handle animation (an agent "resizing" an element)
8. Skin variants: blueprint / terminal / light canvas
9. Orchestration timeline
10. Reduced-motion mapping

---

## 1. Selection engine: principle and extensions

**Principle**: the box does not follow the element's CSS; it is measured every frame.

```
read:  r  = el.getBoundingClientRect()          // already includes the offset we applied
       fr = r - applied offset                    // final layout position
write: box.transform = translate3d(fr.left + T.x, fr.top + T.y + scrollY, 0)    // document space; use the current T, not this frame's r, or the box lags a frame
       only touch width/height and the label text when they change (avoid forcing overlay layout every frame)
```

**Why not `position:absolute` inside the element**: then the box participates in content layout, changing wrapping and height, and gets clipped by any parent `overflow`. A fixed overlay with `pointer-events:none` does not affect content at all.

**Key points**
- **Hug the text**: block elements stretch inside a flex column. Use `h1/h2/h3[data-node]{width:fit-content;max-width:100%}` and `section > [data-node]{align-self:flex-start}`.
- **Nested nodes**: if parent and child both carry `data-node`, the two boxes overlap. Either tag only the outer element, or style child boxes more faintly: `.sel.child{background:transparent;border-style:dashed}`, deciding in `makeBox()` via `el.parentElement.closest('[data-node]')`.
- **Show the element type in the label**: replace the `dim` text with `h1 · 705 × 235`: `n.box.lastChild.textContent = n.el.tagName.toLowerCase()+' · '+w+' × '+h`.
- **Only box what is on screen**: the template already filters with `n.vis`. With many nodes (>60), replace the per-frame `getBoundingClientRect()` with an `IntersectionObserver` that maintains `vis`, and only read rects for visible nodes.
- **Label hidden by the bottom edge**: when `r.bottom + 28 > innerHeight`, flip the label above the box: `dim.style.transform='translate(-50%,-100%) translateY(-8px)'` and set `top` to `0`.

## 2. Agent cursors: personality and variants

Cursor motion is made of **time-based eased segments** (`seg()`), not springs; the mechanics are in `agent-drag.md` section 3. This section is about making each agent different.

**Give each agent its own "personality"** (this is where the narrative comes from): add fields in `CONFIG.agents` and attach the config when creating the agent object: `return {el, ring: el.firstChild, cfg: a, i, ...}` (i.e. add `cfg: a`).

```js
{name:'perf', color:'#ff9f1c', speed:1.4, dwell:[150,400]}    // crisp and quick
{name:'a11y', color:'#4cc9f0', speed:.8,  dwell:[800,1600]}   // slow and deliberate
```
Then in `claim()` divide the flight time by the speed: `clamp(dist / CONFIG.fly.speed, min, max) / (a.cfg.speed ?? 1)`; in `wander()` / `finish()` use `a.cfg.dwell ?? CONFIG.dwell`. **Do not** change drag durations: drag duration belongs to the element, and varying it makes elements dragged by different cursors feel inconsistent.

**Make a cursor own a category of element** (stronger narrative): filter the queue in `claim()` by element type, e.g. the `type` cursor only claims headings, `a11y` only buttons and form fields, `3d` only `#hero3d`. If nothing in the queue qualifies, it keeps wandering. Now the name tag matches what the cursor carries, and viewers read it without being told.

**Cursor trail** (optional, cheap): add a `.trail` child to `.cur` and vary `transform: translate(-vx*3px, -vy*3px)` and `opacity` with speed. Do not create new nodes.

**Count and legibility**: beyond ~16 cursors it becomes noise. If you want "a big crowd", use 8–12 plus occasional "leave/join" (fade out over 400ms, fade in elsewhere).

## 3. Glitch slicing

### 3a. Single layer (template default, cheapest)
Pseudo-elements duplicate the text, and two layers (blue/red) cut horizontal bands with `clip-path: inset()` and offset them:

```css
[data-glitch].glitching::before,
[data-glitch].glitching::after{ content:attr(data-text); position:absolute; inset:0; white-space:pre-wrap; font:inherit; letter-spacing:inherit; line-height:inherit; pointer-events:none }
[data-glitch].glitching::before{ color:#5b8cff; animation:gl1 .56s steps(2,end) both }
[data-glitch].glitching::after { color:#ff3b30; mix-blend-mode:screen; animation:gl2 .56s steps(2,end) both }
```
When triggering from JS you must write `data-text` first, and **use `innerText`** (`textContent` swallows `<br>` and the line breaks come out wrong).

Key points: `steps(2,end)` makes the offset jump instead of slide, which is what reads as tearing; duration ≤ 0.6s.

### 3b. Multi-layer slicing (closer to the "pixel tearing" strips in the recording)
Clone the heading into N slice layers (N=4–6), each showing one horizontal band and shifting randomly:

```js
function sliceGlitch(el, n = 5, ms = 520){
  const h = el.offsetHeight, layers = [];
  for (let i = 0; i < n; i++){
    const c = el.cloneNode(true);
    c.removeAttribute('data-node'); c.removeAttribute('data-glitch'); c.setAttribute('aria-hidden','true');
    c.style.cssText = `position:absolute;inset:0;pointer-events:none;margin:0;opacity:1;filter:none;transform:none;` +
      `clip-path:inset(${(i/n*100).toFixed(1)}% 0 ${(100-(i+1)/n*100).toFixed(1)}% 0)`;
    el.appendChild(c); layers.push(c);
  }
  const t0 = performance.now();
  (function step(now){
    const p = (now - t0) / ms;
    layers.forEach(c => c.style.transform = p < 1 ? `translateX(${((Math.random()*2-1)*18*(1-p)).toFixed(1)}px)` : 'none');
    if (p < 1) requestAnimationFrame(step); else layers.forEach(c => c.remove());
  })(t0);
}
```
Note: cloning briefly doubles the DOM, so use it only on a few large headings. Clones must be `aria-hidden` and must lose `data-node` (otherwise they get measured as new nodes). `el` needs `position:relative`.

### 3c. RGB split (optional)
On top of 3a, add `text-shadow: -2px 0 #f0f, 2px 0 #0ff`, enabled only while `.glitching`.

## 4. Scramble decode and count-up

The template's `scramble(el)`: every frame, characters that are "not yet decoded" are replaced with random glyphs, while decode progress `p` advances linearly.
- **Only use it on mono micro-labels**: with proportional fonts, changing character widths make the text wiggle and the box width jump.
- Including `▮▯░▒▓` in the glyph set reads more like "rendering" than plain letters.
- Always write the `final` text back when decoding finishes (the template does), so no random characters survive.

`countUp`: cubic ease-out `1 - (1-p)^3`, duration ~1.1s. Years use integers (`data-dec` defaults to 0); percentages use `data-dec="1"` with `data-suffix="%"`. In reduced motion, write the final value directly (the template does).

## 5. Scanline, rulers and coordinate readout

**Scanline** (template): on a screen change, a red vertical line sweeps left to right, ~900ms, once. Use WAAPI, not a looping CSS animation; looping turns it into a screensaver and burns more power.

**Rulers** (blueprint feel, optional): add 20px tick strips along the top and left of `#dlf` (the viewport-space overlay; putting them in `#dl` would scroll them away), drawing ticks with `repeating-linear-gradient`:
```css
.ruler-x{position:absolute;left:20px;right:0;top:0;height:20px;background:repeating-linear-gradient(90deg,#2a3142 0 1px,transparent 1px 10px);opacity:.5}
```

**Real cursor coordinate readout**: follow the pointer with a small `x: 812  y: 304` label, updating `transform` on `pointermove`. Enable on desktop only (`matchMedia('(pointer:fine)')`).

## 6. Click-to-select: letting visitors "circle" elements

Turn the page from "watched" into "playable": in Design view, a click on any `data-node` keeps that node's box lit and shows handles and an inspector.

```js
let picked = null;
document.addEventListener('click', e => {
  if (!designMode) return;
  const el = e.target.closest('[data-node]'); if (!el) return;
  e.preventDefault();
  picked = nodes.find(n => n.el === el);
  picked.until = Infinity;                       // keep the box lit
  $('#inspector').textContent =
    `${el.tagName.toLowerCase()}  ${Math.round(picked.fr.width)}×${Math.round(picked.fr.height)}\n` +
    `font ${getComputedStyle(el).fontSize}  color ${getComputedStyle(el).color}`;
}, true);
```
`#inspector` is a small panel fixed to the bottom-right (mono, `pre-wrap`). Note: intercept clicks only in `designMode`, otherwise links and buttons break.

## 7. Drag handle animation (an agent "resizing" an element)

After arriving, have an agent "grab" the bottom-right handle and drag it, scaling the box slightly and settling back (purely visual; the real DOM is untouched):

```js
function nudge(n){
  if (!n.box || !n.box.animate) return;
  n.box.animate(                                  // a ring expanding outward, as if the element is being resized
    [{boxShadow:'0 0 0 0 rgba(47,107,255,.65)'},
     {boxShadow:'0 0 0 9px rgba(47,107,255,0)'}],
    {duration:520, easing:'cubic-bezier(.3,.7,.2,1)'});
}
```
Call `nudge(n)` inside `grab()` (after `pulse(a)`), so the grab moment emits a ring. The box element has no outline, so do not try `outline-offset` for this; nothing visible would happen.
A more faithful version draws a "dashed preview box" outside the real box, scaled by the agent's offset and faded on release. **Never actually resize the element**: that causes layout jitter, gets picked up by the read phase, and creates a feedback loop.

## 8. Skin variants

Change only tokens and a few rules; the mechanics stay the same.

| Skin | `--bg` | `--blue` (boxes) | Type | Notes |
|---|---|---|---|---|
| Blueprint | `#0a1f44` | `#7ee7ff` | Mostly mono | Add a `32px` grid background; boxes use `border-style:dashed` |
| Terminal | `#050805` | `#35ff7a` | All mono | Scanline turns green; scramble glyph set becomes `01{}[]<>` |
| Light canvas | `#f4f4f6` | `#7c5cff` | Sans | Reads like a Figma light canvas; glitch layers using `mix-blend-mode:screen` should switch to `multiply` |

On light skins, re-derive contrast for `#hud` and `.sel .dim` text and backgrounds; do not reuse the dark values.

## 9. Orchestration timeline

There is no longer "one `build()` per screen". Each element runs its own pipeline, and the rhythm comes from three values: **claim interval** (`claimGap`), **flight duration** and **drag duration**. A typical first screen (11 elements, 12 cursors), in ms, from the default config, ~2.0s measured total:

```
 0     page loads, 11 elements queue at once, the red scanline sweeps
 0–70  cursor 1 claims the topmost element (nav logo); a dashed ghost box appears at its spawn point
 70…   every 70ms another cursor claims the next element (a relay)
 340–880 cursors fly to their spawn points
 +90   grab pause, element appears (headline glitches, label scrambles, number starts counting)
 +620–980 dragged home
 +450  box fades out
≈2000  first screen fully in place
```
**Principles**
- **Top to bottom.** The queue is sorted by on-screen position, so the viewer's eye naturally travels down.
- **The most important element carries the strongest effect** (the headline's glitch). Everything else relies on being dragged in.
- Do not give every element a different entrance animation in the name of "depth". The uniform "grabbed and dragged in" is the narrative.

**"Wireframe → finished" variant**: before being grabbed, show an element briefly as a skeleton (`outline:1px dashed` + `color:transparent`). The template's dashed ghost box is the light version of this; a heavier version delays the first-screen text, so avoid it on the Hero headline if LCP matters.

## 10. Reduced-motion mapping

| Normal | `prefers-reduced-motion: reduce` |
|---|---|
| Per-element reveal + boxes | Everything shown immediately, no boxes (the Design button still opens static boxes manually) |
| Agent cursors | Not created (`agentCount = 0` in the template) |
| Scanline / glitch / scramble | Disabled |
| Count-up | Final value shown directly |
| 3D rotation | A single static frame |
