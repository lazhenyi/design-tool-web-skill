# 3D 主视觉(3d-hero)

起步模板的主视觉是**程序化**生成的(没有外部模型文件):蓝色缠绕结 + 一根细尖塔 + 6 个金色发光节点。好处是零下载、可发布、可用参数微调。想换形体时按下面选方案。

## 目录
1. 模板里的缠绕结:参数与坑
2. 换形体方案 A:粒子场(InstancedMesh)
3. 换形体方案 B:起伏的发光球(ShaderMaterial)
4. 换形体方案 C:加载 glTF 模型
5. 与滚动联动
6. 性能预算与降级
7. 版本差异提醒

---

## 1. 模板里的缠绕结:参数与坑

```js
new THREE.TorusKnotGeometry(R, tube, tubularSegments, radialSegments, P, Q)
// 模板: R=.95, tube=.2, 220, 24, P=2, Q=3
```

| 想要 | 改法 |
|---|---|
| 更粗/更细的管 | `tube` 在 .12–.32;**金色节点球半径必须大于 `tube`**,否则被管吞没(模板:节点 .27 > 管 .2) |
| 更复杂的缠绕 | 改 `P,Q`(整数,互质时才是单根结),如 (3,4)、(2,5) |
| 更圆滑 | 提高 `tubularSegments`(最多 ~300),三角形数随之线性增加 |

**节点怎么贴在结上**:用与 `TorusKnotGeometry` 相同的参数方程,否则节点会飘离管道:

```js
const u  = i / N * P * Math.PI * 2;      // 参数范围是 [0, 2πP],不是 [0, 2π]
const qp = Q / P * u, cs = Math.cos(qp);
x = R * (2 + cs) * .5 * Math.cos(u);
y = R * (2 + cs) * Math.sin(u) * .5;
z = R * Math.sin(qp) * .5;
```
把 `u` 范围写成 `[0, 2π]` 是常见错误,节点只会分布在结的一半上。

**发光**:每个节点再叠一个更大的球(`scale≈1.9`),材质 `MeshBasicMaterial` + `transparent` + `depthWrite:false` + **`blending: THREE.AdditiveBlending`**。用普通透明混合时光晕会发闷发棕,不像发光。

**视差**:模板用 `pointermove` 驱动目标旋转 `tx/ty`,再用 `current += (target - current) * .05` 缓动。别直接赋值,否则鼠标一动模型就"抽"。

## 2. 方案 A:粒子场(InstancedMesh)

单个 draw call 画几百个小点,适合"数据/星尘"主题:

```js
const N = 600, geo = new THREE.IcosahedronGeometry(.022, 0);
const inst = new THREE.InstancedMesh(geo, new THREE.MeshBasicMaterial({color: 0x7aa2ff}), N);
const m = new THREE.Matrix4(), seed = [];
for (let i = 0; i < N; i++) seed.push({r: 1.8 + Math.random() * 2.2, th: Math.random() * 6.283, ph: Math.acos(2 * Math.random() - 1), s: .2 + Math.random()});
scene.add(inst);
// 每帧(draw 里):
seed.forEach((p, i) => {
  const th = p.th + t * .0001 * p.s;
  m.makeTranslation(p.r * Math.sin(p.ph) * Math.cos(th), p.r * Math.cos(p.ph), p.r * Math.sin(p.ph) * Math.sin(th));
  inst.setMatrixAt(i, m);
});
inst.instanceMatrix.needsUpdate = true;
```
粒子数 300–800 足够;超过 2000 在中低端手机上开始吃力。

## 3. 方案 B:起伏的发光球(ShaderMaterial)

不引入噪声库,用三个正弦相乘做低成本位移:

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
// 每帧: mat.uniforms.uT.value = t * .001;
```
`ShaderMaterial` 不会自动做输出编码转换,颜色会比 `MeshStandardMaterial` 略偏,按眼睛调 `uA/uB` 即可。位移在顶点着色器里算,GPU 开销很低;不要改成 CPU 每帧改顶点。

## 4. 方案 C:加载 glTF 模型

用户提供了品牌模型时才用。r128 的 `GLTFLoader` 不在 `three.min.js` 里,要额外引入(jsDelivr 是发布页面允许的脚本源之一,仍须锁定版本):

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
```
```js
new THREE.GLTFLoader().load(url, g => { g.scene.scale.setScalar(1.2); group.add(g.scene); });
```
- 模型体积 **< 2MB**、三角形 **< 100k**。更大要先在 Blender 里减面、压缩纹理。
- 单文件页面里可把小模型转成 data URI 内嵌;但超过 ~1MB 就不划算,应改成外部文件托管。
- 带 Draco 压缩的模型需要额外的解码器文件,在受限环境里容易失败。能不压就不压,或用未压缩的 `.glb`。
- 加载期间先显示降级的 CSS 光球,加载完再淡入画布,避免首屏空洞。

## 5. 与滚动联动

```js
// draw() 里:
const s = Math.min(1, scrollY / innerHeight);      // 第一屏内 0→1
cam.position.z = 6.3 + s * 1.4;                    // 滚动时镜头拉远
group.rotation.z = s * .6;
```
不要做"滚动劫持"(接管滚轮、锁页面)——它破坏无障碍和原生手感,在手机上尤其糟糕。只做"读 scrollY 并映射到参数"。

## 6. 性能预算与降级

| 项 | 预算 |
|---|---|
| 三角形 | < 100k(模板实测约 1.9 万) |
| draw call | < 50(模板实测 14) |
| 像素比 | `Math.min(devicePixelRatio, 2)`;低端手机可用 1.5 |
| 画布尺寸 | ≤ 540px 边长(模板),不要全屏铺 |
| 渲染时机 | 仅当画布在视口内、标签页可见(模板已用 IntersectionObserver + `document.hidden`) |

**降级链**(都已在模板里,改造时别删):
1. `three.min.js` 没加载 → `THREE` 未定义 → 给 `<html>` 加 `.no-webgl` → 显示 CSS 径向渐变光球。
2. `new WebGLRenderer` 抛错(无 WebGL)→ 同上。
3. 减少动态模式 → 渲染一帧静态画面,不再 tick。

建议再补一条:

```js
renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); document.documentElement.classList.add('no-webgl'); });
```

**销毁**(单页用不到,做 SPA/路由切换时必须):对每个几何体/材质调 `.dispose()`,最后 `renderer.dispose()`,必要时 `renderer.forceContextLoss()`,否则会泄漏显存。

## 7. 版本差异提醒

模板固定使用 **three r128**(cdnjs 上的版本,经过测试)。如果改用更新的版本:

- 输出色彩空间 API 改名:r128 是 `renderer.outputEncoding = THREE.sRGBEncoding`;较新版本是 `renderer.outputColorSpace = THREE.SRGBColorSpace`。
- 较新版本的光照默认按物理单位计算,**灯光强度数值要重新调**,不能直接沿用模板里的 `1.25 / 1.0 / 2.2`。
- cdnjs 上较新的版本可能只提供模块构建,不提供 `three.min.js` 的全局脚本;此时需要改成 ES 模块 + 打包器(见 `stack-and-scaling.md`)。
- 任何版本都要**写死精确版本号**,并选择发布至少两周的版本。
