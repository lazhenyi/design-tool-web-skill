# Agent drag orchestration and cluster gather (agent-drag)

This is the core mechanic: **every element on the page is grabbed and dragged into place by one agent cursor; at the bottom of the page all cursors converge into a single cluster.** The starter template already implements all of it. This document explains why it works that way, what each parameter controls, and how to change it.

## Contents
1. Why "fade in + drifting cursor" fails
2. Element lifecycle
3. Cursor lifecycle
4. Sync: why the cursor never leaves its element
5. Coordinates: why the overlay must be in document space
6. Choosing spawn points (no overflow, no page growth)
7. Bottom gather
8. Parameter table
9. Variants
10. Pitfalls

---

## 1. Why "fade in + drifting cursor" fails

The early version had two problems, neither fixable by tuning numbers:

1. **The causality was fake.** The element faded in on its own while a cursor drifted randomly nearby. The eye looks for "who made this appear", finds nothing, and reads the page as fake and noisy.
2. **The entrance used `filter: blur`.** Animating blur is one of the easiest ways to drop frames. Animate only `transform` and `opacity`, which can be done on the compositor.

So the new approach makes **causality real**: the element appears because a cursor grabbed it and dragged it over; the element's offset and the cursor's position come from the same value.

## 2. Element lifecycle

```
hidden ─(enters viewport)→ queued ─(claimed by an agent)→ claimed ─(agent flies to spawn point and grabs)→ drag ─(released)→ done
```

| State | What you see | What happens |
|---|---|---|
| `hidden` | Invisible, at its final position | Not yet in the viewport; nothing happens |
| `queued` | Invisible | Entered the viewport (top edge above 92% of viewport height), queued, sorted "topmost first" |
| `claimed` | Invisible, **but a dashed ghost box appears at the spawn point** | An agent is flying there; the ghost box tells the viewer something will appear here |
| `drag` | Visible, with a solid selection box, handles and size label | 90ms grab pause, then an ease-out drag to the final position |
| `done` | Normal | The box lingers `linger` ms and fades; `transform` is cleared |

Key points:
- **Lazy trigger.** An element is only queued when it enters the viewport. Lower screens are not "built" while nobody is looking.
- **Skip on scroll-past.** If the element has already scrolled out of view when its turn comes, it is shown with `instant()`, wasting none of an agent's motion.
- Element offsets use **`translate3d` only**; `will-change: transform` is set during the drag and cleared afterwards.

## 3. Cursor lifecycle

Each agent is a small state machine:

```
wander ──new job──▶ claim → fly (to spawn point) → grab → drag → release → dwell → wander …
```

- **All motion is time-based eased segments** (`seg()`), never springs. Springs overshoot, jitter and depend on frame rate; a time-interpolated eased path with a small perpendicular arc (`arc`) looks like a hand moving and is predictable.
- **New work beats wandering.** Wander segments are tagged `idle:true` and can be interrupted at any moment. Otherwise you get "the element has been queued for 2 seconds and the cursor is still wandering".
- **Round-robin claiming.** Only one claim is allowed per `claimGap` (default 70ms), so 12 cursors depart one after another and read as a relay. **Cursors waiting in the queue must wait in place; they must not be sent off to wander** (a real early bug: only the first cursor won the claim in a frame, the other 11 were sent wandering, and the first screen took over 3.5s to build; ~2.0s after the fix).
- **Grab point.** A random point inside the element, biased toward the top-left (capped at 180×70px), so the cursor holds "a corner of the element", not its center.
- **Name tags.** Shown only while working (`.working`) or in Design view, so the screen does not fill with text.

## 4. Sync: why the cursor never leaves its element

During a drag, the element's offset `T` and the cursor's position come from the same calculation and are written in the same frame:

```js
// order within the frame
T = D * (1 - ease(progress))                       // element offset (D is the spawn offset)
cursor = layoutRect.topLeft + grabOffset + T        // cursor = the element's current grab point
element.style.transform = translate3d(T)            // written in the same frame
```

Details that matter:
- **`layoutRect` must be the "final layout position"**, not the current bounding box. The rect you read already contains the offset we applied, so subtract it: `fr.left = rect.left - appliedX`. This subtraction is only exact because offsets are pure translations (no rotation, no scale).
- **The selection box is also positioned from `fr + current T`**, not from the rect read this frame. The rect read this frame still has the previous frame's offset and would lag by one frame.
- **While dragging, `gk` (the gather blend factor) is forced to 0**, so the cursor is exactly the grab point.

That is precisely what the QA script measures: the **real DOM distance** between cursor and grab point during a drag. The template measures 0.07px max, including during wheel scrolling.

## 5. Coordinates: why the overlay must be in document space

This is the easiest thing to miss and the one with the biggest effect on smoothness.

- If the overlay is `position: fixed` (viewport space), scrolling is done asynchronously on the **compositor thread**, while cursor positions are computed on the **main thread** every frame. Elements move with the compositor; cursors wait for the next main-thread frame. So **cursors lag by one frame of scroll** and appear to slide across the element. Measured: up to 70px of drift while scrolling and dragging.
- The fix: put the overlay in **`position: absolute` inside `body` (`position: relative`)** and position boxes and cursors in **document coordinates** (viewport coordinates + `scrollY`). Cursor and element then live in the same scroll layer, and their relative position depends only on drag progress, independent of scrolling. Measured drift: 0.07px.

```css
body{position:relative}
#dl {position:absolute;inset:0;z-index:60;pointer-events:none;overflow:clip;contain:layout style}  /* document space */
#dlf{position:fixed;inset:0;z-index:60;pointer-events:none;overflow:hidden}                         /* boxes for fixed nodes only */
```
```js
box.style.transform    = `translate3d(${fr.left+T.x}px, ${fr.top+T.y + (node.fixed ? 0 : sy)}px, 0)`;
cursor.style.transform = `translate3d(${a.x}px, ${a.y + sy}px, 0)`;     // viewport coords internally, scrollY added on write
```
- `overflow: clip` crops cursors that fly beyond the document edge so they cannot enlarge the page.
- **Fixed nodes** (top bar, HUD) do not scroll, so their boxes go into `#dlf`. They are only dragged in at load time, when scrolling is unlikely, so keeping their cursors in the document layer is acceptable.

## 6. Choosing spawn points (no overflow, no page growth)

An element's spawn point = final position + offset `D` (150–300px desktop, 70–140px mobile, direction picked from 8 candidates). Candidates are filtered:

| Filter | Why |
|---|---|
| Left and right edges must be inside the viewport (non-fixed elements) | Otherwise the offset creates horizontal scrollable overflow, which widens the mobile layout viewport |
| A downward offset must not go below the bottom of the document | Otherwise the offset makes the document taller and the scroll range jumps |
| The vertical span of the spawn point must intersect the viewport | The spawn point has to be visible |
| If everything is filtered out, fall back to an upward offset | Upward never increases the scrollable area |

Additionally, `main{overflow-x:clip}` acts as a last safety net.

## 7. Bottom gather

At the end of the page there is a "stage" element `[data-gather]` (dashed frame, four corner handles, a caption). It is **not** a dragged node; it is static and fades in with gather progress.

**Gather progress `G` is determined by the stage's own position**, not by pixels from the bottom of the page:

```js
toBottom = DOCH - (scrollY + vh)                // how much further to the bottom
aFinal   = anchorY - toBottom                    // where the stage center will be at the bottom
G = smooth(clamp((vh - anchorY) / (vh - aFinal), 0, 1))   // stage just entered = 0, at bottom = 1
```
This way the gather **starts when the stage enters the viewport** and **finishes exactly at the bottom**, independent of viewport height. If you used "N pixels from the bottom", cursors would fly toward a point off-screen.

Each cursor's gather factor `gk` is staggered:

```js
stagger = smooth(clamp(G*1.35 - (i/n)*0.35, 0, 1))      // arrive one after another, not all at once
gk += (stagger - gk) * (1 - Math.exp(-dt*.22))            // then smooth once more
displayPos = workPos + (clusterSlot - workPos) * gk
```
- **Slots** are laid out with phyllotaxis: `radius = spacing*√(i+0.6)`, angle `i*2.39996`, with slow overall rotation and a slight breathing motion. Twelve cursors form one clump, with the farthest about 50px from the center.
- Because it is **scroll-driven and continuous**, cursors spread back out smoothly when you scroll up, and hold position if you stop midway. There is no trigger and no state switch.
- **No new drags start while gathering**: when `G > 0.6`, the rest of the queue is shown with `instant()`.
- **Cursors still easing out of the cluster (`gk` not yet decayed) may not claim** (`gk < 0.02`), otherwise the cluster pulls them off target when the drag starts.
- When all `gk > 0.96`, `<body>` gets `.gathered`: each cursor emits a pulse ring, the stage caption reads "N agents online · all synced", and the HUD state becomes `synced`.

## 8. Parameters

| Parameter | Default | Meaning / tuning |
|---|---|---|
| `claimGap` | 70ms | Minimum gap between claims. Smaller feels like simultaneous grabbing, larger like a relay |
| `fly.speed` | 1.5 px/ms | Flight speed toward the spawn point; the result is clamped to `[min,max]` = 340–880ms |
| `drag.hold` | 90ms | Pause after the grab, so the viewer sees "it has been grabbed" |
| `drag.min/max` | 620–980ms | Drag duration, growing with distance (`480 + distance×1.1`) |
| `spawn.desktop / small` | 150–300 / 70–140px | How far from its final position an element spawns |
| `linger` | 450ms | How long the box stays after release |
| `wander / dwell` | 900–1900 / 250–900ms | Idle wandering and dwelling |
| `gatherSpacing` | 15px | Spacing between cursors in the cluster; larger is looser |
| `agents / agentsSmall` | 12 / 7 | Cursor count. Measured: the first screen (11 elements) builds in ~2.0s with 12 desktop cursors, ~2.2s with 7 on mobile |

The drag easing `1 - (1-p)^2.6`: fast start, slow landing, like a hand setting something down. There is a 90ms pause before the grab, so the quick start is justified.

## 9. Variants

- **Pulling elements out of a toolbar.** Instead of a random direction, spawn points always point at a palette icon (for example a column of icons on the left of the screen); the cursor picks the element up from the icon and drags it into place. Only `pickSpawn` needs to return an icon-directed offset, plus a palette UI.
- **Two cursors cooperating.** For large elements (like `.media`), assign two agents, one on the top-left and one on the bottom-right, each hugging its own grab point. `n.agent` becomes an array and both share the same `T`.
- **Snap at the end of a drag.** Add a tiny overshoot and settle in the last 8% of progress (≤4px). Make the cursor follow the same overshoot, or sync breaks.
- **Do something after gathering.** When everyone arrives, have the cursors form a ring and point at a button in the center of the stage, or take turns "typing" inside it. The slot function is pure; swap in any other arrangement.

## 10. Pitfalls

- **Several cursors competing for one claim slot in a frame.** Queued cursors must wait where they are, not wander (see section 3).
- **Wandering that cannot be interrupted.** A new element waits 2 seconds with nobody attending it. Wander segments must carry an `idle` flag and be interruptible.
- **Cursors sliding during scroll.** The overlay must be in document space (see section 5).
- **Cursor drifting at the start of a drag.** A cursor still held by the cluster (`gk>0`) drifts after claiming. Require `gk<0.02` before claiming and force `gk=0` while dragging.
- **Writing `transform` on a node in CSS.** It gets overwritten by JS. Center with `margin:auto` / `inset`, not `translate(-50%,-50%)`. The 3D container and the HUD were both changed for this reason.
- **Offsets causing overflow.** See section 6.
- **Using `p95` to judge smoothness.** Frame intervals are quantized (16.7 / 33.3ms), so a single stutter doubles p95. Look at the slow-frame share and the maximum.
- **Breaking the failure fallback.** The 5-second fallback reveal must only fire if the main loop never started; firing unconditionally reveals every element that has not been scrolled to yet, and the drag-in is gone.
