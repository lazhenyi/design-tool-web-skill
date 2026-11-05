# Stack and scaling (stack-and-scaling)

The default single-file template is enough for a contest-grade single page. Upgrade only in the cases below.

## Contents
1. When to upgrade
2. Moving the overlay to React
3. 3D: React Three Fiber
4. Scroll and orchestration libraries (GSAP / Lenis)
5. SSR, SEO and share images
6. Version pinning and CSP (hard constraints for published pages)
7. Deployment

---

## 1. When to upgrade

| Need | Recommendation |
|---|---|
| One page, contest or showcase, publishable as a link | **Stay on the single-file template** |
| Multiple pages, routing, CMS, blog | Vite or Next + React, with the overlay as a component |
| Complex 3D (several models, post-processing, interaction) | React Three Fiber (or vanilla three with modules) |
| Team collaboration, types and tests | TypeScript + a bundler |

**Do not upgrade for sophistication.** The bottleneck for pages like this is pacing, narrative and taste, not engineering effort. The cost of upgrading is losing "a single file is a release".

## 2. Moving the overlay to React

The algorithm is framework-agnostic: **attribute the elements to be dragged, measure final layout positions every frame, keep the overlay in document space, and compute cursor position and element offset from the same value** (see `agent-drag.md`). The template's main loop moves into a `useEffect` in one component.

```tsx
'use client'
import { useEffect, useRef } from 'react'

export function DesignLayer() {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const root = ref.current!
    let raf = 0
    const tick = (t: number) => {
      const sy = scrollY
      // 1. read: rects of all [data-node], minus applied offsets → final layout positions
      // 2. queue, claim, drag progress, step agents (template frame() steps 1–4)
      // 3. write: element transforms, box and cursor transforms (add sy to y, i.e. document space)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])
  // Note: this must NOT be position:fixed. Scrolling is done by the compositor, and cursors
  // in a fixed overlay lag the elements by one frame of scroll.
  return <div ref={ref} id="dl" aria-hidden="true" style={{ position: 'absolute', inset: 0, overflow: 'clip', pointerEvents: 'none', zIndex: 60 }} />
}
```
The skeleton only shows the structure; take the full state machine (`hidden → queued → claimed → drag → done`), claim rules, sync writes and gather straight from the template's `frame()`.

**Key points**
- **Boxes and cursors are created imperatively, not owned by React**: otherwise React's reconciliation fights the per-frame style writes.
- **Dragged elements get their `transform` written by JS**, so their CSS must not set `transform` (center with `margin:auto` / `inset`), and React's `style` prop must not manage `transform` either, or every re-render overwrites it.
- **Dynamic content**: when elements come and go, cache the node list with a `MutationObserver` instead of re-querying every frame.
- **Route changes**: re-collect nodes and reset state on mount; cancel the rAF and remove boxes and cursors on unmount.
- **A `position:relative` ancestor must wrap the overlay** (`body` in the template), or document-space coordinates are wrong.

## 3. 3D: React Three Fiber

The template's knot maps directly to an R3F component, with unchanged geometry and material parameters:

```tsx
<Canvas dpr={[1, 2]} camera={{ position: [0, 0, 6.3], fov: 36 }}>
  <ambientLight intensity={0.55} />
  <mesh><torusKnotGeometry args={[0.95, 0.2, 220, 24, 2, 3]} /><meshStandardMaterial color="#2f6bff" metalness={0.55} roughness={0.28} /></mesh>
</Canvas>
```
Note: newer three versions changed the semantics of light intensity, so **values must be re-tuned** (see `3d-hero.md` section 7). Stop rendering while the canvas is not visible (switch `frameloop` or check visibility yourself), same as the single-file version.

## 4. Scroll and orchestration libraries (GSAP / Lenis)

- **GSAP is not required**: the template's drag orchestration is its own state machine and does not depend on a timeline library. If you do switch to timeline-driven, **cursor position and element offset must still come from the same progress value**, or sync breaks.
- **Smooth-scroll libraries such as Lenis**: they drive scrolling with JS. In principle a document-space overlay scrolls with the document and should stay compatible, but **this skill has not tested any smooth-scroll library**. Smooth scrolling also changes native feel and needs care on mobile and with screen readers, and must be off under reduced motion. After enabling it, re-run the drag-sync check in `preview.py`.
- Do not do **scroll hijacking** (taking over the wheel, locking the page): it breaks accessibility.

## 5. SSR, SEO and share images

- **Content is real DOM**, so server rendering makes it indexable. That is this method's advantage over a full-page canvas.
- The overlay, agents and 3D are **client-only**: in Next, put them in client components so they are absent from the first HTML response.
- The reveal hiding state (`.js [data-node]{opacity:0}`) depends on `<html class="js">`. **That class must be added before first paint** (inline script in `<head>`), otherwise content flashes visible then hidden. In Next, use an inline script in `<head>`.
- The OG image needs a static file. Crop one from a `scripts/preview.py` screenshot; do not generate it live.

## 6. Version pinning and CSP (hard constraints for published pages)

When a page is published as an Artifact, the host enforces these rules. Break them and the page publishes but stops working:

- External scripts may only come from `cdnjs.cloudflare.com` (preferred), `cdn.jsdelivr.net/npm/`, `cdn.tailwindcss.com`, `code.jquery.com`; external styles only from Google Fonts. **Everything else (unpkg, esm.sh, remote images, requests to other domains) is silently blocked.**
- All script URLs must **pin an exact version**: no `latest`, no ranges, no tags. Pick a version released **at least two weeks ago** (a brand-new release may carry malicious code that nobody has caught yet).
- Libraries must be **global-script (UMD) builds**, not ES module imports.
- Inline images and data as `data:` URIs; total file size < 16MB.
- Do not use `window.storage` or requests to `api.anthropic.com` (unavailable in published pages). For persistence, use only `localStorage` (wrapped in `try/catch`) for single-user convenience features.

Self-hosted sites have none of these constraints, but **pinning exact versions** is still good practice. With a bundler, install dependencies at exact versions (`npm install --save-exact`).

## 7. Deployment

Static hosting is enough (any provider). Before deploying:
1. Run `scripts/preview.py` and go through `qa-checklist.md`.
2. Confirm `<title>`, `description`, the OG image and the favicon.
3. If hosted under a subpath, check relative paths and `#` anchor jumps.
4. Enable gzip/brotli. The single-file template is small; most of its weight is three (~600KB uncompressed).
