# InkGrid Web

> InkGrid 前端 —— Next.js 14 App Router 实现的"博客 + AI 知识库问答"界面。

骨架阶段，使用 mock 数据；后端与 AI 链路接入后替换为真实 API。

## 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 框架 | **Next.js 14.2** (App Router) | SSG / SSR / CSR 混合渲染 |
| 语言 | TypeScript 5.5 | 全量类型 |
| UI 组件 | Ant Design 5 + lucide-react | 后台用 AntD；博客前台用 Tailwind 定制风格 |
| 样式 | Tailwind CSS 3.4 | Obsidian Spatial 设计 token |
| 字体 | Geist (UI) + JetBrains Mono (技术标签) | `next/font` 自托管 |
| 状态管理 | Zustand 4.5 | 客户端交互态（问答 / 语音） |
| 请求 | Axios 1.7 | 客户端 REST 请求 |
| 实时通信 | 原生 WebSocket | 文字流式 + 语音流式 |
| 博客 Markdown | MDX + next-mdx-remote + Shiki | SSG 预渲染，质感优先 |
| 对话 Markdown | react-markdown + remark-gfm + rehype-highlight | CSR 流式增量渲染 |
| 编辑器 | Bytemd | 源码 + 预览分屏，GFM/数学/Mermaid/高亮插件 |
| 全文搜索 | Meilisearch | 中文分词、即时搜索 |
| 图标 | @ant-design/icons + lucide-react | 线性风格 |

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式（默认 http://localhost:3000）
npm run dev

# 生产构建
npm run build
npm run start

# Lint
npm run lint
```

## 环境变量

`.env.development` 与 `.env.production` 已就绪，关键变量：

```bash
NEXT_PUBLIC_API_BASE        # 后端 API 根（dev: http://localhost:8000，prod: /api）
NEXT_PUBLIC_WS_BASE        # WebSocket 根（dev: ws://localhost:8000，prod: /ws）
NEXT_PUBLIC_MEILI_HOST     # Meilisearch 地址
NEXT_PUBLIC_MEILI_KEY      # Meilisearch key（公开搜索只读 key）
NEXT_PUBLIC_SITE_NAME       # 站点名（默认 inkgrid.dev）
NEXT_PUBLIC_SITE_AUTHOR     # 博主署名（默认 张三）
NEXT_PUBLIC_SITE_VERSION    # 站点版本号
```

## 目录结构

```
web/
├── app/                              # App Router 路由与页面
│   ├── (public)/                     # 公开站点路由组（博客前台）
│   │   ├── layout.tsx                #   公开站点布局（Navbar + Footer）
│   │   ├── page.tsx                  #   首页（hero + 全站问答入口 + 文章流）
│   │   ├── posts/
│   │   │   ├── page.tsx              #     文章列表（SSG）
│   │   │   └── [slug]/page.tsx       #     文章详情（SSG，含末尾问 AI）
│   │   ├── channel/[slug]/page.tsx   #     频道页（SSG/ISR）
│   │   ├── about/page.tsx            #     关于
│   │   └── search/page.tsx           #     搜索（CSR，Meilisearch）
│   ├── (chat)/                       # AI 对话路由组
│   │   ├── layout.tsx                #   对话布局（沉浸式，去网格淡化）
│   │   ├── ask/
│   │   │   ├── page.tsx              #     文字问答页（CSR，流式）
│   │   │   ├── persona/page.tsx      #     人设档案选择
│   │   │   └── voice/page.tsx        #     语音通话页（CSR，全屏沉浸）
│   ├── admin/                        # 博主后台（CSR + 鉴权）
│   │   ├── layout.tsx                #   后台布局（侧栏 + 顶栏）
│   │   ├── page.tsx                  #   数据看板
│   │   ├── posts/                    #   文章管理
│   │   ├── knowledge/                #   知识库管理
│   │   ├── channels/                 #   频道管理
│   │   ├── persona/                  #   人设配置
│   │   ├── policy-collector/         #   政策采集管理
│   │   └── settings/                 #   站点设置
│   ├── login/page.tsx                # 登录
│   ├── layout.tsx                    # 根布局（字体 + metadata）
│   ├── providers.tsx                 # AntD Next.js Registry
│   └── globals.css                   # 全局样式 + 设计 token
├── components/
│   ├── layout/                       # Navbar / Footer
│   ├── blog/                         # ArticleCard / ArticleShell / TableOfContents
│   ├── chat/                         # AskBox / RoleCard
│   └── admin/                       # Placeholder
├── lib/
│   ├── api/request.ts                # Axios 实例（拦截器、会话 ID）
│   ├── mock.ts                       # 骨架阶段 mock 数据
│   ├── theme.ts                      # AntD 主题配置
│   ├── usePersona.ts                 # 人设选择 hook（localStorage 持久化）
│   └── utils.ts                      # 通用工具（cn 等）
├── types/index.ts                    # 全局类型（Article / Channel / Persona / ChatMessage…）
├── middleware.ts                     # 鉴权中间件：拦截 /admin/* → /login
├── next.config.js
├── tailwind.config.ts                # Obsidian Spatial 设计 token
├── tsconfig.json
└── package.json
```

## 路由与渲染策略

| 路由 | 渲染 | 鉴权 | 说明 |
|------|------|------|------|
| `/` | SSG/ISR | 公开 | 首页：文章流 + 全站问答入口 |
| `/posts` | SSG/ISR | 公开 | 文章列表 |
| `/posts/[slug]` | **SSG** | 公开 | 文章详情，`generateStaticParams` 预生成 |
| `/channel/[slug]` | SSG/ISR | 公开 | 频道页 |
| `/ask` | **CSR** | 公开 | 问答页（流式交互） |
| `/ask/voice` | **CSR** | 公开 | 语音通话页（全屏沉浸） |
| `/ask/persona` | CSR | 公开 | 人设档案 |
| `/search` | CSR | 公开 | Meilisearch 即时搜索 |
| `/about` | SSG | 公开 | 关于博主 |
| `/admin/*` | CSR | 博主 | 后台，middleware 鉴权 |
| `/login` | CSR | 公开 | 登录 |

## 设计系统：Obsidian Spatial

源文档：`../plan/DESIGN.md`

- **底色**：`#121414` 纯黑微紫，最大化 OLED 对比
- **网格**：白色 6% 透明线，铺于背景营造空间感（文章阅读区与后台去掉网格）
- **几何**：零圆角，所有元素对齐 4px 基准、8px 模数
- **层级**：靠 `bg-surface-container-*` 亮度差 + 1px 边框分层，不用 box-shadow
- **字体**：
  - `font-sans` / `font-headline` → Geist（UI 与标题）
  - `font-mono` → JetBrains Mono（Logo / 导航数字 / 标签 / 代码）
- **间距 token**：`base` 4px、`grid-minor` 8px、`grid-major` 32px、`gutter` 24px、`margin-mobile` 16px、`margin-desktop` 48px
- **宽度 token**：`article` 720px、`list` 1100px、`chat` 880px、`admin` 1200px、`page-7xl` 1280px

Tailwind 配置见 [tailwind.config.ts](./tailwind.config.ts)。

## 问答范围模型

AI 问答支持三级检索范围，由入口决定：

| 入口 | 范围 | 场景 |
|------|------|------|
| 全站问答框（首页 / 导航） | 全站所有已发布文章 | 综合提问 |
| 频道问答区 | 该频道内文章 + 专属数据 | 场景化提问 |
| 文章末尾"问 AI" | 单篇文章 + 关联推荐 | 深入提问 |

`ChatScope` 类型见 [types/index.ts](./types/index.ts)。

## 鉴权

- 公开站点无鉴权
- `/admin/*` 由 [middleware.ts](./middleware.ts) 拦截，未登录跳 `/login?redirect=...`
- 博主 token 存 httpOnly cookie（生产由后端 Set-Cookie），中间件校验
- 公开问答用匿名会话 ID（localStorage `anon_session_id`，请求头 `X-Session-Id`）

## 通信层

### REST

`lib/api/request.ts` 封装 Axios：
- `baseURL` 来自 `NEXT_PUBLIC_API_BASE`
- 请求拦截器注入匿名会话 ID
- 响应拦截器统一错误处理

服务端组件优先用 `fetch() + next.revalidate`，配合 Next.js 缓存。

### WebSocket（流式）

文字流式问答连接：`wss://host/ws/chat?scope=global|channel:xxx|article:xxx`

```ts
// C → S
{ type: 'user_message', content: 'xxx' }
{ type: 'stop' }

// S → C
{ type: 'token', content: 'xxx' }
{ type: 'citation', data: {...} }
{ type: 'followup', questions: [...] }
{ type: 'clarify', content: '...', options: [...] }
{ type: 'done' }
{ type: 'error', message: '...' }
```

语音流式通话：二进制音频帧 + JSON 控制帧混传（首字节区分），详见 [plan/前端模块设计文档.md](../plan/前端模块设计文档.md) 第八节。

## 开发规范

1. **服务端 / 客户端组件**：默认 RSC，需要交互才加 `'use client'`，避免不必要水合。
2. **命名**：组件 PascalCase，hooks 以 `use` 开头。
3. **类型**：禁止 `any`，API 响应有 interface。
4. **样式**：博客前台用 Tailwind + 设计 token；后台沿用 AntD。
5. **流式渲染**：统一走 hooks，禁止组件直接操作 WebSocket。
6. **MDX**：博客文章插件链与 Bytemd 编辑器插件链保持一致，保证所见即所得。

## 部署

### 本地

```bash
npm run build
npm run start   # 或 PM2 托管
```

### 生产（Nginx 示例）

```nginx
location / { proxy_pass http://nextjs:3000; }       # Next.js server
location /api/ { proxy_pass http://backend:8000; }  # FastAPI
location /ws/ {
  proxy_pass http://backend:8000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_read_timeout 3600s;
}
location /meili/ { proxy_pass http://meilisearch:7700; }
```

## 关联文档

- [产品与技术方案](../plan/产品与技术方案.md)
- [前端模块设计文档](../plan/前端模块设计文档.md)
- [设计系统 DESIGN.md](../plan/DESIGN.md)
