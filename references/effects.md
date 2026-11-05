# 特效配方(effects)

代码片段沿用起步模板里的变量名:`nodes`(每个节点有 `fr` 最终布局矩形、`T` 当前位移、`state`、`until`)、`agents`、`CONFIG`、`reveal(n)`、`pulse(a)`、`dl`(文档空间覆盖层)、`dlf`(视口空间覆盖层)。直接粘进模板的 IIFE 里即可。**拖入编排与汇聚的机制本身见 `agent-drag.md`**,这份只讲在它之上的特效与变体。

## 目录
1. 选框引擎:原理与扩展
2. 代理光标:物理与"性格"
3. 故障切片:单层与多层
4. 乱码解码与数字滚动
5. 扫描线、标尺与坐标读数
6. 点击选中:让访客也能"圈"元素
7. 拖拽手柄动画(代理"调整"元素)
8. 皮肤变体:蓝图 / 终端 / 浅色画布
9. 编排时间线
10. 减少动态模式的映射

---

## 1. 选框引擎:原理与扩展

**原理**:选框不是跟着元素的 CSS 走的,而是每帧量出来的。

```
读:  r  = el.getBoundingClientRect()          // 已含我们自己施加的位移
     fr = r - 已施加的位移                     // 最终布局位置
写:  box.transform = translate3d(fr.left + T.x, fr.top + T.y + scrollY, 0)    // 文档空间;用"当前 T"而不是本帧读到的 r,否则框会落后一帧
     宽高变了才改 width/height 与标签文字(避免每帧触发覆盖层布局)
```

**为什么不用 `position:absolute` 贴在元素里**:那样框会参与内容布局,改变换行与高度,也会被父级 `overflow` 裁掉。覆盖层固定定位 + `pointer-events:none` 则完全不影响内容。

**要点**
- **贴合文字**:块级元素在 flex 列里会被拉伸。`h1/h2/h3[data-node]{width:fit-content;max-width:100%}`,`section > [data-node]{align-self:flex-start}`。
- **嵌套节点**:父子都带 `data-node` 时,两个框会叠在一起。要么只标最外层,要么给子框更淡的样式:`.sel.child{background:transparent;border-style:dashed}`,在 `makeBox()` 里按 `el.parentElement.closest('[data-node]')` 判断。
- **标签显示元素类型**:把 `dim` 文字改成 `h1 · 705 × 235`:`n.box.lastChild.textContent = n.el.tagName.toLowerCase()+' · '+w+' × '+h`。
- **只框视口内的**:模板已用 `n.vis` 过滤;节点很多(>60)时,把 `getBoundingClientRect()` 换成 `IntersectionObserver` 维护 `vis`,只对可见节点读矩形。
- **标签被屏幕底边挡住**:当 `r.bottom + 28 > innerHeight` 时,把标签翻到框上方:`dim.style.transform='translate(-50%,-100%) translateY(-8px)'`,同时把 `top` 设为 `0`。

## 2. 代理光标:性格与变体

光标的运动是**按时间缓动的片段**(`seg()`),不是弹簧;机制见 `agent-drag.md` 第 3 节。这里只讲怎么让每个 agent 不一样。

**给每个代理不同"性格"**(叙事感的来源):在 `CONFIG.agents` 里加字段,并在创建 agent 对象时挂上配置:`return {el, ring: el.firstChild, cfg: a, i, ...}`(即多加一个 `cfg: a`)。

```js
{name:'perf', color:'#ff9f1c', speed:1.4, dwell:[150,400]}    // 动作利落
{name:'a11y', color:'#4cc9f0', speed:.8,  dwell:[800,1600]}   // 慢条斯理
```
然后在 `claim()` 里把飞行时长除以速度:`clamp(dist / CONFIG.fly.speed, min, max) / (a.cfg.speed ?? 1)`;在 `wander()` / `finish()` 里把停留范围换成 `a.cfg.dwell ?? CONFIG.dwell`。**不要**改拖拽时长——拖拽时长属于元素,改了会让不同光标拖出的元素节奏不一致。

**让某个光标专管某类元素**(更强的叙事):`claim()` 里挑队列时按元素类型过滤,例如 `type` 光标只认领标题、`a11y` 只认领按钮与表单、`3d` 只认领 `#hero3d`。队列里没有它能认领的就继续闲逛。这样名牌和它拖的东西对得上,观众会不自觉地读懂。

**光标拖尾**(可选,开销小):给 `.cur` 加一个 `.trail` 子元素,用 `transform: translate(-vx*3px, -vy*3px)` 与 `opacity` 随速度变化,不要创建新节点。

**数量与可读性**:超过 ~16 个会变成噪点。想要"人很多"的感觉,用 8–12 个 + 偶尔出现的"离开/加入"(淡出 400ms 后在别处淡入)即可。

## 3. 故障切片

### 3a. 单层(模板默认,最省)
伪元素复制文本,两层(蓝/红)用 `clip-path: inset()` 切出水平条带并错位:

```css
[data-glitch].glitching::before,
[data-glitch].glitching::after{ content:attr(data-text); position:absolute; inset:0; white-space:pre-wrap; font:inherit; letter-spacing:inherit; line-height:inherit; pointer-events:none }
[data-glitch].glitching::before{ color:#5b8cff; animation:gl1 .56s steps(2,end) both }
[data-glitch].glitching::after { color:#ff3b30; mix-blend-mode:screen; animation:gl2 .56s steps(2,end) both }
```
JS 触发时必须先写 `data-text`,**用 `innerText`**(`textContent` 会吞掉 `<br>`,换行就错了)。

要点:`steps(2,end)` 让位移"跳"而不是"滑",才像撕裂;时长 ≤ 0.6s。

### 3b. 多层切片(更接近录屏里"像素撕裂"的碎条)
把标题复制成 N 个切片层(N=4–6),每层只显示一条水平带,各自随机横向位移:

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
注意:克隆会让 DOM 暂时翻倍,所以只用在少数大标题上;克隆体必须 `aria-hidden`,且要去掉 `data-node`(否则会被当成新节点测量)。`el` 需要 `position:relative`。

### 3c. RGB 分离(可选)
在 3a 上再加一层 `::selection` 无关的 `text-shadow: -2px 0 #f0f, 2px 0 #0ff`,仅在 `.glitching` 时启用。

## 4. 乱码解码与数字滚动

模板的 `scramble(el)`:每帧把"尚未解码"的字符替换为随机字形,解码进度 `p` 线性推进。
- **只用于等宽字体的小标签**:比例字体下字符宽度变化会让文字抖动、选框宽度乱跳。
- 字形集合里加入 `▮▯░▒▓` 比纯字母更像"渲染中"。
- 解码完成后一定要写回 `final`(模板已做),避免残留随机字符。

`countUp`:三次缓出 `1 - (1-p)^3`,时长 ~1.1s。年份用整数(`data-dec` 缺省 0);百分比用 `data-dec="1"` 与 `data-suffix="%"`。减少动态模式下直接写终值(模板已做)。

## 5. 扫描线、标尺与坐标读数

**扫描线**(模板):换屏时一条红色竖线从左扫到右,~900ms,一次性。用 WAAPI,不要用循环 CSS 动画——循环会变成"屏保",也更耗电。

**标尺**(蓝图感,可选):在 `#dlf`(视口空间覆盖层)里加顶部和左侧两条 20px 的刻度条(放 `#dl` 的话标尺会随页面滚走),用 `repeating-linear-gradient` 画刻度:
```css
.ruler-x{position:absolute;left:20px;right:0;top:0;height:20px;background:repeating-linear-gradient(90deg,#2a3142 0 1px,transparent 1px 10px);opacity:.5}
```

**真实鼠标的坐标读数**:在鼠标旁跟一个 `x: 812  y: 304` 的小标签,`pointermove` 里更新 `transform`。仅桌面启用(`matchMedia('(pointer:fine)')`)。

## 6. 点击选中:让访客也能"圈"元素

让页面从"被看"变成"可玩":访客在 Design 视图下点任意 `data-node`,该节点的框常亮并出现手柄和检查器。

```js
let picked = null;
document.addEventListener('click', e => {
  if (!designMode) return;
  const el = e.target.closest('[data-node]'); if (!el) return;
  e.preventDefault();
  picked = nodes.find(n => n.el === el);
  picked.until = Infinity;                       // 常亮
  $('#inspector').textContent =
    `${el.tagName.toLowerCase()}  ${Math.round(picked.fr.width)}×${Math.round(picked.fr.height)}\n` +
    `font ${getComputedStyle(el).fontSize}  color ${getComputedStyle(el).color}`;
}, true);
```
`#inspector` 是一块固定在右下角的小面板(等宽字体、`pre-wrap`)。注意:点击拦截只在 `designMode` 下生效,否则会破坏链接与按钮。

## 7. 拖拽手柄动画(代理"调整"元素)

到达节点后,让某个代理"抓住"右下手柄并拖动,框的尺寸缩放一下再回弹(纯视觉,不改真实 DOM):

```js
function nudge(n){
  if (!n.box || !n.box.animate) return;
  n.box.animate(                                  // 向外扩散的一圈光晕,模拟"被拖动调整"
    [{boxShadow:'0 0 0 0 rgba(47,107,255,.65)'},
     {boxShadow:'0 0 0 9px rgba(47,107,255,0)'}],
    {duration:520, easing:'cubic-bezier(.3,.7,.2,1)'});
}
```
在 `grab()` 里(`pulse(a)` 之后)调用 `nudge(n)`,让"抓住"那一刻有一圈光晕扩散。选框元素本身没有 outline,所以别用 `outline-offset` 做这个效果——那样不会有任何可见变化。
更逼真的做法是在框外再画一个"虚线预览框",随代理的位移缩放,松手后淡出。注意**不要真的去改元素尺寸**——那会造成布局抖动并被读阶段捕获,形成反馈环。

## 8. 皮肤变体

只改 token 与少量规则,机制不变。

| 皮肤 | `--bg` | `--blue`(选框) | 字体 | 说明 |
|---|---|---|---|---|
| 蓝图 | `#0a1f44` | `#7ee7ff` | 等宽为主 | 背景加 `32px` 网格;选框用虚线 `border-style:dashed` |
| 终端 | `#050805` | `#35ff7a` | 全等宽 | 扫描线改绿色;乱码字形集换成 `01{}[]<>` |
| 浅色画布 | `#f4f4f6` | `#7c5cff` | 无衬线 | 像 Figma 浅色画布;`mix-blend-mode:screen` 的故障层改 `multiply` |

浅色皮肤时,`#hud` 与 `.sel .dim` 的文字/背景要重新取对比度,别沿用深色的值。

## 9. 编排时间线

不再有"一屏一个 `build()`"。每个元素各自走自己的流水线,节奏由三个量决定:**认领间隔**(`claimGap`)、**飞行时长**、**拖拽时长**。首屏(11 个元素、12 个光标)的典型时间线(ms;各段取自默认配置,总耗时约 2.0s 为实测):

```
 0     页面加载,11 个元素同时进入队列,红色扫描线扫过
 0–70  第 1 个光标认领最靠上的元素(顶栏 logo),起点处出现虚线幽灵框
 70…   每隔 70ms 又一个光标认领下一个元素(接力)
 340–880 各光标飞到各自的起点
 +90   抓取停顿,元素出现(标题带故障切片、标签带乱码解码、数字开始滚动)
 +620–980 拖到位
 +450  选框淡出
≈2000  首屏全部到位
```
**原则**
- **从上到下**:队列按屏幕上的位置排序,所以观众的视线自然从顶往下走。
- **最重要的元素带最强的特效**(标题的故障切片),其余只靠"被拖入"本身。
- 不要为了"更有层次"而给每个元素加不同的入场动画;统一的"被抓住、被拖入"才是叙事主线。

**"线框→成品"变体**:元素被抓住前先以 `outline:1px dashed` + `color:transparent` 显示一小会儿(纯骨架)。模板里的虚线幽灵框已经是它的轻量版本;更重的版本会让首屏文字更晚出现,对首屏 LCP 敏感时不要用在 Hero 标题上。

## 10. 减少动态模式的映射

| 常规 | `prefers-reduced-motion: reduce` |
|---|---|
| 逐个 reveal + 选框 | 全部直接显示,无选框(Design 按钮仍可手动打开静态选框) |
| 代理光标 | 不创建(模板 `agentCount = 0`) |
| 扫描线 / 故障 / 乱码 | 关闭 |
| 数字滚动 | 直接显示终值 |
| 3D 自转 | 渲染静帧 |
