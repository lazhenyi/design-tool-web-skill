# 技术栈与扩展(stack-and-scaling)

默认的单文件模板能做完一个参赛级单页。只有在下面这些情况下才升级。

## 目录
1. 什么时候升级
2. 覆盖层如何迁移到 React
3. 3D:React Three Fiber
4. 滚动与编排库(GSAP / Lenis)
5. SSR、SEO 与分享图
6. 版本固定与 CSP(发布页面的硬约束)
7. 部署

---

## 1. 什么时候升级

| 需求 | 建议 |
|---|---|
| 一页、参赛/展示、要能直接发布成链接 | **留在单文件模板** |
| 多页、路由、CMS、博客 | Vite 或 Next + React,覆盖层做成组件 |
| 复杂 3D 场景(多模型、后处理、交互) | React Three Fiber(或原生 three + 模块) |
| 团队协作、需要类型与测试 | TypeScript + 打包器 |

**不要因为"高级"而升级。** 这类页面的瓶颈是节奏、叙事和审美,不是工程量。升级的代价是失去"单文件即发布"的便利。

## 2. 覆盖层如何迁移到 React

算法与框架无关:**给要被拖入的元素加属性,每帧测量最终布局位置,覆盖层放在文档空间,光标与元素位移由同一数值算出**(见 `agent-drag.md`)。模板的主循环可以整体搬进一个组件里的 `useEffect`。

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
      // 1. 读:所有 [data-node] 的矩形,减去已施加的位移 → 最终布局位置
      // 2. 排队、认领、拖拽进度、代理步进(同模板 frame() 的 1–4 步)
      // 3. 写:元素 transform、选框与光标的 transform(y 要加 sy,即文档空间)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])
  // 注意:不能是 position:fixed。滚动由合成器完成,fixed 覆盖层里的光标会落后元素一帧的滚动量。
  return <div ref={ref} id="dl" aria-hidden="true" style={{ position: 'absolute', inset: 0, overflow: 'clip', pointerEvents: 'none', zIndex: 60 }} />
}
```
骨架里只写了结构;完整的状态机(`hidden → queued → claimed → drag → done`)、认领规则、同步写法和汇聚都直接照模板的 `frame()` 搬。

**要点**
- **选框与光标由命令式代码创建,不交给 React 管理**:否则 React 的协调会和每帧写样式打架。
- **被拖入的元素自己的 `transform` 由 JS 写**:所以这些元素的 CSS 里不能再写 `transform`(居中用 `margin:auto` / `inset`),也不要让 React 的 `style` 属性管它们的 `transform`,否则每次重渲染都会被覆盖。
- **动态内容**:元素会增减时,把节点列表用 `MutationObserver` 缓存,别每帧重新查询。
- **路由切换**:挂载后重新收集节点并重置状态,卸载时取消 rAF 并移除选框与光标。
- **必须有一个 `position:relative` 的祖先包住覆盖层**(模板里是 `body`),否则文档空间的坐标会错位。

## 3. 3D:React Three Fiber

模板里的缠绕结可以直接改写为 R3F 组件,几何与材质参数不变:

```tsx
<Canvas dpr={[1, 2]} camera={{ position: [0, 0, 6.3], fov: 36 }}>
  <ambientLight intensity={0.55} />
  <mesh><torusKnotGeometry args={[0.95, 0.2, 220, 24, 2, 3]} /><meshStandardMaterial color="#2f6bff" metalness={0.55} roughness={0.28} /></mesh>
</Canvas>
```
注意:较新的 three 版本光照强度语义变了,**数值要重新调**(见 `3d-hero.md` 第 7 节)。让画布在不可见时停止渲染(`frameloop` 切换或自行判断可见性),与单文件版本同理。

## 4. 滚动与编排库(GSAP / Lenis)

- **GSAP** 不是必需的:模板的拖入编排是自己的状态机,不依赖时间线库。真要换成时间线驱动,要保证**光标位置与元素位移仍由同一个进度值算出**,否则会破坏同步。
- **Lenis 等平滑滚动库**:它们用 JS 驱动滚动。从原理上讲,文档空间覆盖层随文档一起滚动,应当兼容,但**本 skill 没有对任何平滑滚动库做过实测**。但平滑滚动会改变原生手感,在手机和读屏场景要谨慎,并在减少动态模式下关闭;启用后也要重跑 `preview.py` 的拖拽同步检查。
- 不要做**滚动劫持**(接管滚轮、锁定页面):破坏无障碍。

## 5. SSR、SEO 与分享图

- **内容是真实 DOM**,服务端渲染即可被索引——这是该方法相对"整页 canvas"的优势。
- 覆盖层、代理、3D 都是**仅客户端**:在 Next 里放进客户端组件,首屏 HTML 里不含它们。
- 揭示用的隐藏态(`.js [data-node]{opacity:0}`)依赖 `<html class="js">`。**这个类要在首次绘制前加上**(放在 `<head>` 里的内联脚本),否则会闪一下"先显示再隐藏"。在 Next 里用 `<head>` 内联脚本实现。
- 分享图(OG image)需要一张静态图。可用 `scripts/preview.py` 产出的截图裁剪,不要现场生成。

## 6. 版本固定与 CSP(发布页面的硬约束)

当页面要作为 Artifact 发布时,宿主强制以下规则,违反则页面能发布但功能失效:

- 外部脚本只允许来自 `cdnjs.cloudflare.com`(优先)、`cdn.jsdelivr.net/npm/`、`cdn.tailwindcss.com`、`code.jquery.com`;外部样式只允许 Google Fonts。**其他一切(unpkg、esm.sh、远程图片、其他域的请求)都会被静默拦截。**
- 所有脚本 URL **写死精确版本**,不要用 `latest`、范围或标签;选发布**至少两周**的版本(新发布的版本可能带恶意代码而尚未被发现)。
- 库要用**全局脚本(UMD)**构建,不能用 ES 模块 import。
- 图片和数据用 `data:` URI 内嵌;文件总大小 < 16MB。
- 不要使用 `window.storage` 与对 `api.anthropic.com` 的请求(发布页面里不可用);需要持久化时只用 `localStorage`(并包 `try/catch`)做单人便利功能。

自己托管的站点没有这些限制,但**锁定精确版本**仍是好习惯。用打包器时,依赖用精确版本安装(`npm install --save-exact`)。

## 7. 部署

静态托管即可(任何静态托管服务)。部署前:
1. 跑 `scripts/preview.py` 并过一遍 `qa-checklist.md`;
2. 确认 `<title>`、`description`、OG 图、favicon;
3. 如果托管在子路径下,检查相对路径与 `#` 锚点跳转;
4. 开启 gzip/brotli;模板单文件很小,主要体积来自 three(约 600KB 未压缩)。
