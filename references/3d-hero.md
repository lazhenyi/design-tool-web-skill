# 3D hero (3d-hero)

The starter's hero is **procedural** (no external model files): a blue interlaced knot, a thin spire and 6 glowing gold nodes. The benefit is zero downloads, publishable anywhere, and parameters you can tweak. When you want a different form, pick one of the options below.

## Contents
1. The template's knot: parameters and pitfalls
2. Option A: particle field (InstancedMesh)
3. Option B: a swelling glowing sphere (ShaderMaterial)
4. Option C: loading a glTF model
5. Tying it to scroll
6. Performance budget and degradation
7. Version differences to watch

---

## 1. The template's knot: parameters and pitfalls

```js
new THREE.TorusKnotGeometry(R, tube, tubularSegments, radialSegments, P, Q)
// template: R=.95, tube=.2, 220, 24, P=2, Q=3
```

| Want | Change |
|---|---|
| Thicker/thinner tube | `tube` between .12 and .32; **the gold node sphere radius must exceed `tube`**, or nodes are swallowed by the tube (template: node .27 > tube .2) |
| More intricate winding | Change `P,Q` (integers; only coprime pairs give a single knot), e.g. (3,4), (2,5) |
| Smoother | Raise `tubularSegments` (up to ~300); triangle count grows linearly |

**How nodes sit on the knot**: use the same parametric equations as `TorusKnotGeometry`, or nodes float off the tube:

```js
const u  = i / N * P * Math.PI * 2;      // the parameter range is [0, 2πP], not [0, 2π]
const qp = Q / P * u, cs = Math.cos(qp);
x = R * (2 + cs) * .5 * Math.cos(u);
y = R * (2 + cs) * Math.sin(u) * .5;
z = R * Math.sin(qp) * .5;
```
Writing the `u` range as `[0, 2π]` is the common mistake: nodes then only cover half the knot.

**Glow**: stack a larger sphere on each node (`scale≈1.9`) with `MeshBasicMaterial` + `transparent` + `depthWrite:false` + **`blending: THREE.AdditiveBlending`**. With normal alpha blending the halo looks dull and brown instead of glowing.

**Parallax**: the template maps `pointermove` to target rotation `tx/ty`, then eases with `current += (target - current) * .05`. Do not assign directly, or the model snaps every time the pointer moves.

## 2. Option A: particle field (InstancedMesh)

Hundreds of small points in a single draw call; good for a "data / stardust" theme:

```js
const N = 600, geo = new THREE.IcosahedronGeometry(.022, 0);
const inst = new THREE.InstancedMesh(geo, new THREE.MeshBasicMaterial({color: 0x7aa2ff}), N);
const m = new THREE.Matrix4(), seed = [];
for (let i = 0; i < N; i++) seed.push({r: 1.8 + Math.random() * 2.2, th: Math.random() * 6.283, ph: Math.acos(2 * Math.random() - 1), s: .2 + Math.random()});
scene.add(inst);
// each frame (in draw):
seed.forEach((p, i) => {
  const th = p.th + t * .0001 * p.s;
  m.makeTranslation(p.r * Math.sin(p.ph) * Math.cos(th), p.r * Math.cos(p.ph), p.r * Math.sin(p.ph) * Math.sin(th));
  inst.setMatrixAt(i, m);
});
inst.instanceMatrix.needsUpdate = true;
```
300–800 particles is plenty; beyond 2000 starts to strain mid-range phones.

## 3. Option B: a swelling glowing sphere (ShaderMaterial)

No noise library: multiply three sines for cheap displacement:

```js
const mat = new THREE.ShaderMaterial({
  uniforms: {uT: {value: 0}, uA: {value: new THREE.Color(0x2f6bff)}, uB: {value: new THREE.Color(0xffb62e)}},
  vertexShader: `
    uniform float uT; varying vec3 vN; varying float vD;
    void main(){
      vec3 p = position;
      float d = sin(p.x*3.0+uT) * sin(p.y*3.0+uT*1.3) * sin(p.z*3.0+uT*.7) * .18;
      p += normal * d; vD = d;
      vN = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
    }`,
  fragmentShader: `
    uniform vec3 uA, uB; varying vec3 vN; varying float vD;
    void main(){
      float f = pow(1.0 - abs(dot(normalize(vN), vec3(0.,0.,1.))), 2.0);
      vec3 c = mix(uA, uB, smoothstep(-.1, .18, vD)) + f * .35;
      gl_FragColor = vec4(c, 1.0);
    }`
});
scene.add(new THREE.Mesh(new THREE.IcosahedronGeometry(1.2, 5), mat));
// each frame: mat.uniforms.uT.value = t * .001;
```
`ShaderMaterial` does not do output color encoding automatically, so colors skew slightly compared with `MeshStandardMaterial`; tune `uA/uB` by eye. Displacement runs in the vertex shader, so GPU cost is low; do not move it to CPU vertex updates.

## 4. Option C: loading a glTF model

Only when the user provides a brand model. In r128, `GLTFLoader` is not in `three.min.js` and must be loaded separately (jsDelivr is one of the allowed script sources for published pages, but still pin the version):

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
```
```js
new THREE.GLTFLoader().load(url, g => { g.scene.scale.setScalar(1.2); group.add(g.scene); });
```
- Model size **< 2MB**, triangles **< 100k**. Anything larger needs decimating and texture compression in Blender first.
- For single-file pages, small models can be inlined as a data URI; beyond ~1MB that stops paying off and the model should be hosted externally.
- Draco-compressed models need an extra decoder file and fail easily in restricted environments. Avoid compression, or ship an uncompressed `.glb`.
- Show the CSS fallback globe while loading and fade the canvas in afterwards, so the first screen is never empty.

## 5. Tying it to scroll

```js
// inside draw():
const s = Math.min(1, scrollY / innerHeight);      // 0→1 within the first screen
cam.position.z = 6.3 + s * 1.4;                    // pull the camera back as you scroll
group.rotation.z = s * .6;
```
Do not do **scroll hijacking** (taking over the wheel, locking the page). It breaks accessibility and native feel, and is especially bad on mobile. Only read `scrollY` and map it to parameters.

## 6. Performance budget and degradation

| Item | Budget |
|---|---|
| Triangles | < 100k (template measures ~19k) |
| Draw calls | < 50 (template measures 14) |
| Pixel ratio | `Math.min(devicePixelRatio, 2)`; 1.5 on low-end phones |
| Canvas size | ≤ 540px per side (template); do not fill the screen |
| Render timing | Only while the canvas is in the viewport and the tab is visible (template uses IntersectionObserver + `document.hidden`) |

**Degradation chain** (all in the template; do not delete it when customizing):
1. `three.min.js` fails to load → `THREE` undefined → add `.no-webgl` to `<html>` → show the CSS radial-gradient globe.
2. `new WebGLRenderer` throws (no WebGL) → same as above.
3. Reduced motion → render one static frame, stop ticking.

One more worth adding:

```js
renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); document.documentElement.classList.add('no-webgl'); });
```

**Disposal** (irrelevant for a single page, mandatory for SPAs and route changes): call `.dispose()` on every geometry and material, then `renderer.dispose()`, and `renderer.forceContextLoss()` if needed, or you leak GPU memory.

## 7. Version differences to watch

The template pins **three r128** (the version available on cdnjs, and tested). If you move to a newer version:

- The output color space API was renamed: r128 uses `renderer.outputEncoding = THREE.sRGBEncoding`; newer versions use `renderer.outputColorSpace = THREE.SRGBColorSpace`.
- Newer versions compute lighting in physical units by default, so **light intensities must be re-tuned**; the template's `1.25 / 1.0 / 2.2` do not carry over.
- Newer versions on cdnjs may only ship module builds, without a global `three.min.js`; that requires ES modules plus a bundler (see `stack-and-scaling.md`).
- Whatever version you use, **pin the exact version number**, and pick a release that has been out for at least two weeks.
