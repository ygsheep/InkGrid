---
---
name: Obsidian Spatial
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#383939'
  surface-container-lowest: '#0d0e0f'
  surface-container-low: '#1b1c1c'
  surface-container: '#1f2020'
  surface-container-high: '#292a2a'
  surface-container-highest: '#343535'
  on-surface: '#e3e2e2'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#e3e2e2'
  inverse-on-surface: '#303031'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c6c6c7'
  primary: '#ffffff'
  on-primary: '#2f3131'
  primary-container: '#e2e2e2'
  on-primary-container: '#636565'
  inverse-primary: '#5d5f5f'
  secondary: '#c8c6c5'
  on-secondary: '#313030'
  secondary-container: '#474746'
  on-secondary-container: '#b7b5b4'
  tertiary: '#ffffff'
  on-tertiary: '#003919'
  tertiary-container: '#6bfe9c'
  on-tertiary-container: '#00743a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1c1b1b'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#6bfe9c'
  tertiary-fixed-dim: '#4ae183'
  on-tertiary-fixed: '#00210c'
  on-tertiary-fixed-variant: '#005228'
  background: '#121414'
  on-background: '#e3e2e2'
  surface-variant: '#343535'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.05em
spacing:
  base: 4px
  grid-major: 32px
  grid-minor: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

This design system is built on a "Technical Minimalism" philosophy, specifically tailored for high-performance developer tools, data visualization, and engineering environments. The core aesthetic is **Digital Architecture**: it treats the UI as a 3D coordinate space rather than a flat document.

The brand personality is precise, authoritative, and focused. It avoids visual clutter and decorative imagery, relying instead on structural integrity, mathematical spacing, and high-contrast typography to guide the user. The goal is to evoke a sense of limitless spatial depth and technical clarity.

## Colors

The palette is strictly monochromatic with a "Pure Black" foundation to maximize OLED contrast and reduce visual fatigue. 

- **Surface:** The absolute base is `#000000`. 
- **Typography:** Primary information uses pure white for maximum legibility. Secondary information is significantly dimmed to a mid-grey to create clear information hierarchy.
- **Accents:** Functional colors (like success or warnings) are used sparingly as 1px strokes or small indicators, never as large fills.
- **Grid:** The background is defined by a persistent technical grid. Use `#FFFFFF` at 7% opacity for major grid lines and 3% for minor subdivisions.

## Typography

The typography system utilizes **Geist** for its clinical precision and balanced kerning. 

- **Headings:** Should be high-contrast (White). Use tight letter spacing for large display type to maintain a "locked-in" architectural feel.
- **Subtitles/Body:** Secondary text must use the dimmed neutral grey to prevent the UI from feeling overwhelming.
- **Technical Data:** Use **JetBrains Mono** for all labels, coordinates, code snippets, and metadata to reinforce the technical nature of the system.

## Layout & Spacing

This design system uses a **Rigid Spatial Grid**. Every element must align to a 4px baseline and an 8px modular scale.

- **Grid System:** On desktop, a 12-column layout is used with 24px gutters. The background grid pattern should align perfectly with these columns.
- **Container Rules:** Avoid centered "page" layouts. Favor edge-to-edge functional zones divided by 1px grey borders.
- **Margins:** Use generous margins (48px+) on desktop to create "dead zones" that emphasize the content's structure. On mobile, tighten margins to 16px but maintain the 8px vertical rhythm.

## Elevation & Depth

In a pure black environment, traditional shadows are ineffective. Depth is instead communicated through **Luminance Tiering** and **Line Work**:

- **Level 0 (Base):** Pure `#000000` with the technical grid.
- **Level 1 (Panels):** Surface color `#0A0A0A` with a 1px solid border of `#1A1A1A`. 
- **Level 2 (Popovers/Modals):** Surface color `#121212` with a 1px border of `#333333`.
- **Interaction:** Use "Inner Glows" (subtle white 1px top border) instead of drop shadows to indicate that an element is raised or active.

## Shapes

The shape language is **Zero-Radius (Sharp)**. 

To maintain the technical, engineered aesthetic, all corners must remain at 0px. This ensures elements align perfectly with the background grid lines. Any perceived "softness" should come from typography and spacing, never from geometry. Use 1px strokes for all containers to maintain a wireframe-like clarity.

## Components

- **Buttons:**
  - **Primary:** Solid White fill with Black text. No border.
  - **Secondary:** Transparent fill with a 1px White border and White text.
  - **Ghost:** Transparent fill, Grey text, appearing White on hover.
- **Input Fields:**
  - Rectangular, 1px border (`#333333`). Labels use `label-mono` style positioned strictly above the field. Active state changes border to pure White.
- **Lists:**
  - Separated by 1px horizontal lines (`#1A1A1A`). Hover states should trigger a subtle `#0A0A0A` background highlight.
- **Chips/Badges:**
  - Use `label-mono` typography. Small, 1px bordered boxes. No rounded corners.
- **Cards:**
  - Cards are simply grid-aligned regions defined by 1px borders. Do not use background fills for cards unless they need to be distinct from the base surface (Level 1 elevation).
- **Data Tables:**
  - Monospaced numerical data. Header cells use a slightly darker background (`#0A0A0A`) and uppercase labels.
---

# Design System

## Overview

一个知识型个人博客 + AI 知识库问答平台，采用**极客暗色风格**：黑色背景叠加白色网格线营造视觉空间感，紫色作为主色调点缀，卡片式布局呈现内容。博客文章即知识库，访客可向 AI 提问，AI 基于文章回答并引用出处。

核心设计意图：
- **极客空间感**：黑色底 + 白色网格线 + 紫色辉光，营造赛博空间般的纵深感，区别于平铺直叙的浅色博客。
- **卡片悬浮**：所有内容以卡片形式悬浮于网格之上，卡片有微妙边框与辉光，像浮在空间中的面板。
- **紫色点睛**：黑底中紫色用于强调（CTA、链接、激活态、辉光），克制不泛滥，让黑色保持主角。
- **阅读区例外**：博客长文阅读区打破暗黑网格，用近黑纯色背景 + 衬线字体，保证长时间阅读舒适。
- **引用溯源第一公民**：AI 答案必须带文章出处，形成"读→问→读"闭环。

## Colors

### 主品牌色（极客紫）
- **primary** (#8B5CF6)：主紫，全站 CTA、链接、用户消息气泡、聚焦态、激活态。
- **primary-glow** (rgba(139,92,246,0.4))：紫色辉光，按钮悬浮/焦点时外发光，极客感的关键。
- 紫色用于"需要被看见"的元素，克制使用，让黑色背景与网格保持主导。

### 频道点缀色
- **accent-channel** (#A855F7)：个人经验频道，亮紫，频道标识点缀。
- **accent-policy** (#22D3EE)：深圳政策频道，青色，与紫形成冷暖对比，区分场景。
- 点缀色仅用于频道图标与入口，不替换主色。

### 语义色（暗色提亮）
- success #34D399、warning #FBBF24、error #F87171：暗底下提亮保证可见性。

### 黑色背景层级（空间感基础）
- **bg-base** (#0A0A0F)：最底层，纯黑微紫，网格画于此。
- **bg-surface** (#12121A)：卡片底，比 base 略亮，让卡片"浮起"。
- **bg-elevated** (#1A1A26)：悬浮弹层，再亮一档。
- 三层黑色形成纵深，配合网格线产生空间感。

### 网格线（视觉空间核心）
- **bg-grid-line** (rgba(255,255,255,0.06))：白色 6% 透明，克制不抢眼，近看可见远看隐没。
- 主页 hero 区网格可做透视变形 + 中心向边缘渐隐，强化空间纵深。

### 文字与边框
- **text-primary** (#F5F5FA)：近白，暗底高对比。
- **border** (rgba(255,255,255,0.08))：白色 8% 透明边框，卡片轮廓。
- **border-primary** (rgba(139,92,246,0.4))：聚焦/激活时紫色边框 + 辉光。

## Typography

### 双字体系统
- **文章正文用衬线**（思源宋体）：17px、1.85 行高。暗色长文阅读用衬线降低疲劳，阅读区背景提亮，保证舒适。
- **UI 用无衬线**（PingFang/微软雅黑）：14–15px，界面清晰。
- **极客等宽**（JetBrains Mono）：用于 Logo、导航数字、代码块、标签。等宽字体是极客风的视觉锚点。

### 极客风应用
- 站点 Logo 与导航用 `display-mono`（等宽 18px），强化极客身份。
- 数字（阅读量、日期）用等宽字体，整齐有"终端感"。

## Spacing & Layout

- 4px 基准单位。
- 文章正文 720px（阅读区），列表 1100px，问答 880px，后台 1200px。
- 卡片间距 24px，卡片内边距 24–32px。
- 网格单元 40px，网格全局铺底，内容区浮于其上。

## Grid Background（视觉空间核心）

主页与频道页使用网格背景营造空间感：

```
固定网格铺底（bg-base 上画 grid-line）
  │
  ├── 中心区域：网格清晰可见
  ├── 边缘区域：网格渐隐至纯黑（fade-radius 600px）
  └── 可选：hero 区透视变形，网格向远处汇聚
      │
      ▼
内容卡片浮于网格之上（bg-surface + border + 微辉光）
```

实现：
- CSS `background-image` 画线性网格，`background-size: 40px 40px`。
- 边缘渐隐用 `mask-image: radial-gradient(...)` 径向遮罩。
- 透视网格用 CSS `transform: perspective(...) rotateX(...)` 可选实现于 hero。
- 网格不动（静态），避免干扰阅读；可加极慢平移（20s）做呼吸感，默认关。

## Components

- **Buttons**：圆角 8px，主按钮紫底白字 + `glow-primary` 辉光；次按钮透明底 + 白色边框。
- **Inputs**：圆角 8px，bg-surface 底，1px border；聚焦变 border-primary + glow。
- **Card**：圆角 12px，bg-surface，1px border；悬浮上移 -2px + border 变亮 + 紫色微辉光。卡片是网格空间中的"浮岛"。
- **Article Card**：纯标题（衬线）+ 副标题/摘要一行 + 等宽日期·频道标签，无封面图，悬浮辉光。极简，靠排版与留白制造质感。
- **Article Content**：720px 居中，bg-article 近黑底，衬线正文，Shiki 高亮（暗色主题如 github-dark）。
- **Message Bubble**：圆角 16px，用户气泡紫底白字，AI 气泡 bg-surface + border。
- **Citation**：📎 + 文章标题，紫色链接，点击展开片段。
- **Nav (极客风)**：等宽字体 Logo，毛玻璃背景（backdrop-blur），滚动后浮起 + 底部紫色渐变线。
- **Status Badge**：圆点 + 文字，三态（绿/黄/红），半透明底色。
- **Voice Call Panel**：全屏，AI 头像紫色光环呼吸 + Canvas 波形。
- **TOC**：右侧悬浮，当前章节紫色高亮 + 左边框。

## Motion

- 卡片出现：fadeIn + slideUp 200ms，可加微妙缩放。
- 卡片悬浮：translateY -2px + border 变亮 + glow-primary 出现，150ms。
- 按钮悬浮：glow-primary 呼吸出现，150ms。
- 紫色辉光：重要元素可加 `glow-pulse` 2s 呼吸动画。
- 语音波形：Canvas + RAF。
- 流式光标：`▋` 闪烁 1s。
- 尊重 `prefers-reduced-motion`，关闭辉光呼吸与网格平移。

## Do's and Don'ts

### Do
- 网格背景仅用于主页/频道/列表页，文章正文页与后台用纯色底（避免干扰阅读）。
- 紫色用于强调，配合 glow 辉光制造极客感，但克制不泛滥。
- 卡片用 bg-surface 浮于 bg-base 之上，靠层级差与边框区分，不用强阴影。
- 文章正文区用 bg-article + 衬线字体，是暗色空间中的"安静阅读区"。
- 极客元素（等宽字体、终端感数字、紫色辉光）用于导航/Logo/元信息，不进正文。
- 间距、圆角、字号必须用 token。
- 三端自适应：移动优先，卡片用 Grid `auto-fill/minmax` 自适应列数，不硬编码断点列数。
- 手机端触摸目标不小于 44×44px，卡片间距与字号按断点缩放。

### Don't
- 不要全站铺网格——文章阅读页和后台必须去掉网格，纯色底。
- 不要紫色大面积铺底（会丢失黑色的空间感，变得浮躁）。
- 不要用浅色/暖色（破坏极客暗色调性）。
- 不要强阴影（暗色风格靠边框与辉光分层，不用 box-shadow 堆叠）。
- 不要文章正文用无衬线（暗底无衬线长文阅读疲劳）。
- 不要让每个 token 触发 React 重渲染（流式文本用 ref 直更 DOM）。
- 不要在语音通话页关闭 echoCancellation。

## Layout Patterns

### 主页（极客网格 + 卡片式）
```
┌──────────────────────────────────────────────────────┐
│  ░░░░░░░░░░░ 网格背景（黑底白线，边缘渐隐）░░░░░░░░░░ │
│  ┌────────────────────────────────────────────────┐  │
│  │  [≡] blog_name.dev    [频道▾][🔍][问AI][🎙][👤]│  │ ← 极客导航（等宽Logo+毛玻璃）
│  └────────────────────────────────────────────────┘  │
│                                                      │
│         ╭────────────────────────────╮               │
│         │  我是张三                  │               │
│         │  记录技术与思考             │   ← hero 紫色辉光
│         │  有问题？问我的 AI ↓       │               │
│         ╰────────────────────────────╯               │
│         ┌──────────────────────────────┐             │
│         │  🤖 向 AI 提问…        [发送]│  ← 紫色主按钮
│         └──────────────────────────────┘             │
│                                                      │
│   最新文章                              查看全部 →    │
│   ┌──────────────────┐ ┌──────────────────┐         │
│   │ 候选人评估三维度  │ │ 深圳人才补贴指南  │         │
│   │ 技术深度、协作…  │ │ 本科15000元/年…  │ ← 纯标题+副标题
│   │ 07-20 · 经验     │ │ 07-18 · 政策     │   等宽日期·频道
│   └──────────────────┘ └──────────────────┘         │
│   ┌──────────────────┐ ┌──────────────────┐         │
│   │ 远程办公实践      │ │ 面试我会问的问题  │         │
│   │ 我倾向于异步…    │ │ 三个维度评估…    │         │
│   │ 07-15 · 随笔     │ │ 07-10 · 经验     │         │
│   └──────────────────┘ └──────────────────┘         │
└──────────────────────────────────────────────────────┘
```

### 文章详情页（阅读区，去网格）
```
┌──────────────────────────────────────────────────────┐
│  [≡] blog_name.dev    [频道▾][🔍][问AI][🎙][👤]      │ ← 导航保留
├──────────────────────────────────────────────────────┤
│  纯黑底（bg-article，无网格）                          │
│                                                      │
│  ┌────────┬─────────────────────────┬────────────┐  │
│  │        │  候选人评估三维度        │            │  │
│  │        │  07-20 · 经验 · 8min    │   目录 TOC  │  │
│  │ 留白   │  ───────────────        │  （紫色     │  │
│  │        │  正文（衬线 720px）      │   高亮）    │  │
│  │        │  代码块/引用/图片        │            │  │
│  │        │  ───────────────        │            │  │
│  │        │  🤖 关于本文还想问？     │            │  │
│  └────────┴─────────────────────────┴────────────┘  │
└──────────────────────────────────────────────────────┘
```

### 问答页（对话型，网格淡化）
```
┌──────────────────────────────────────────────────────┐
│  网格极淡（仅边缘可见）                                │
│  [← 返回]  全站问答                  [切语音 🎙]      │
├──────────────────────────────────────────────────────┤
│                                                      │
│            ┌──────────────────────┐                  │
│            │  对话消息流            │  ← 卡片式气泡    │
│            │  （880px 居中）        │    浮于淡网格上  │
│            └──────────────────────┘                  │
│                                                      │
│            ┌──────────────────────┐                  │
│            │  输入框 + 紫色发送     │                 │
│            └──────────────────────┘                  │
└──────────────────────────────────────────────────────┘
```

### 频道页（网格 + 频道色点缀）
```
┌──────────────────────────────────────────────────────┐
│  网格背景                                              │
│  ┌────────────────────────────────────────────────┐  │
│  │  ◆ 个人经验                              [频道色]│  │ ← 频道色点缀
│  │  记录招聘、协作、工程经验                       │  │
│  │  HR 可直接问 AI，它用我的口吻代答              │  │
│  └────────────────────────────────────────────────┘  │
│        ┌──────────────────────────────┐              │
│        │  🤖 向 AI 提问（频道色边框）  │              │
│        └──────────────────────────────┘              │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│   │ 频道文章卡片  │ │              │ │              ││
│   └──────────────┘ └──────────────┘ └──────────────┘│
└──────────────────────────────────────────────────────┘
```

## Responsive Layout（三端自适应）

移动优先，min-width 向上增强。三端断点：< 768px 手机、768–1023px 平板、≥ 1024px 桌面。

### 主页三端对比

**桌面（≥1024px）— 三列卡片**
```
┌────────────────────────────────────────────┐
│ [≡] blog_name.dev  [频道▾][🔍][问AI][🎙][👤]│
│           我是张三                          │
│     ┌──────────────────────────────┐       │
│     │  🤖 向 AI 提问…        [发送]│       │
│     └──────────────────────────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 文章标题  │ │ 文章标题  │ │ 文章标题  │   │ ← 三列
│  └──────────┘ └──────────┘ └──────────┘   │
└────────────────────────────────────────────┘
```

**平板（768–1023px）— 两列卡片**
```
┌──────────────────────────────────┐
│ [≡] blog_name.dev  [🔍][问AI][👤] │ ← 次要项进菜单
│       我是张三                    │
│   ┌────────────────────────┐     │
│   │  🤖 向 AI 提问…  [发送]│     │
│   └────────────────────────┘     │
│   ┌──────────┐ ┌──────────┐      │
│   │ 文章标题  │ │ 文章标题  │      │ ← 两列
│   └──────────┘ └──────────┘      │
└──────────────────────────────────┘
```

**手机（<768px）— 单列卡片**
```
┌──────────────────────┐
│ blog_name.dev   [≡]  │ ← 汉堡菜单
│   我是张三            │
│ ┌──────────────────┐ │
│ │ 🤖 向 AI 提问…   │ │
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │ 文章标题          │ │ ← 单列
│ │ 副标题…          │ │
│ │ 07-20 · 经验     │ │
│ └──────────────────┘ │
│ ┌──────────────────┐ │
│ │ 文章标题          │ │
│ └──────────────────┘ │
└──────────────────────┘
```

### 文章详情页三端对比

**桌面** — 正文 + 右侧 TOC
```
┌──────────────────────────────────────────┐
│  [≡] blog_name.dev           [问AI][👤]   │
│        ┌─────────────────┬──────────┐    │
│        │  标题（衬线）    │  目录 TOC │    │
│        │  正文 720px      │ （悬浮）  │    │
│        └─────────────────┴──────────┘    │
└──────────────────────────────────────────┘
```

**平板** — 正文 + 右侧 TOC（同桌面，宽度收窄）

**手机** — 单栏，TOC 收进顶部展开
```
┌──────────────────────┐
│ blog_name.dev   [≡]  │
│ [📋 目录 ▾]           │ ← TOC 折叠在顶部
│ ┌──────────────────┐ │
│ │ 标题（衬线）      │ │
│ │ 正文全宽          │ │ ← 单栏无侧边
│ │ 16px 字号         │
│ └──────────────────┘ │
└──────────────────────┘
```

### 语音通话页（三端统一全屏沉浸）

三端均为全屏沉浸，仅布局微调：
- 桌面/平板：AI 头像居中 + 双向字幕左右分布 + 底部控制栏。
- 手机：AI 头像居中偏上 + 双向字幕上下堆叠 + 底部控制栏，适配竖屏。

### 后台三端对比

- **桌面**：固定侧栏 240px + 内容区。
- **平板**：可折叠侧栏（默认收起，点击展开覆盖）。
- **手机**：无侧栏，顶部汉堡抽屉 + 单列内容。

### 响应式通用规则

1. **网格尺寸**：手机 28px、平板 36px、桌面 40px，小屏网格更密保持空间感。
2. **正文字号**：手机 16px、平板/桌面 17px，小屏略缩防溢出。
3. **卡片间距**：手机 12px、平板/桌面 24px。
4. **导航**：桌面完整、平板精简、手机汉堡抽屉。
5. **内容区宽度**：均用 content-max 约束，手机全宽减 padding。
6. **触摸目标**：手机端按钮/链接最小 44×44px（iOS HIG）。
7. **图片**：全部 `next/image` 响应式，手机端图片占满宽度。
8. **流式布局**：用 CSS Grid + `auto-fill/minmax` 实现卡片自适应列数，而非硬编码断点列数。

## Module Theming

全站主色始终是紫色 #8B5CF6，频道色仅作点缀：

| 场景 | 主色 | 频道点缀色 | 网格 |
|------|------|-----------|------|
| 主页 / 全站问答 | 紫 #8B5CF6 | - | 有（主页） |
| 个人经验频道 | 紫（不变） | 亮紫 #A855F7 | 有 |
| 深圳政策频道 | 紫（不变） | 青 #22D3EE | 有 |
| 文章详情页 | 紫（不变） | - | 无（阅读区） |
| 博主后台 | 紫（不变） | - | 无（纯色底） |

点缀色用于：频道图标、频道 hero 边框、问答入口边框。不用于：主按钮、全站链接、用户气泡（始终主紫）。
