import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import ArticleShell from '@/components/blog/ArticleShell';

export interface MockArticle {
  title: string;
  channel: string;
  channelName: string;
  publishedAt: string;
  readingTime: number;
  content: string;
  toc: { id: string; title: string; level: number }[];
  /** 核心概念实体 */
  concepts: string[];
  /** 相关归档文章 */
  relatedPosts: { slug: string; title: string; publishedAt: string }[];
}

// 骨架阶段 mock 数据，接后端后替换为 fetch + SSG + MDX 渲染
const articles: Record<string, MockArticle> = {
  'candidate-eval': {
    title: '候选人评估三维度',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-20',
    readingTime: 8,
    toc: [
      { id: 'intro', title: '为什么需要框架', level: 2 },
      { id: 'tech', title: '技术深度', level: 2 },
      { id: 'collab', title: '协作能力', level: 2 },
      { id: 'growth', title: '成长潜力', level: 2 },
    ],
    content: `
<p>面试一个人，我习惯从三个维度打分。技术只是其中之一。</p>
<h2 id="intro">为什么需要框架</h2>
<p>没有框架的面试容易凭感觉，而感觉往往偏向"像不像自己"。框架的意义在于把主观感受拆成可讨论的客观项。</p>
<h2 id="tech">技术深度</h2>
<p>不是问八股，而是看他能不能把一个技术点讲到<code>底层原理</code>。我会让他画一个他最熟悉系统的架构图，然后追问每一层的取舍。</p>
<blockquote>能讲清楚"为什么这么选"的人，比知道"怎么用"的人值钱十倍。</blockquote>
<h2 id="collab">协作能力</h2>
<p>问一个他经历过的冲突，看他描述对方时的措辞。把别人描述成蠢货的人，通常协作成本很高。</p>
<h2 id="growth">成长潜力</h2>
<p>问他最近半年学的新东西。没有持续学习习惯的人，在快速变化的领域会很快贬值。</p>
`,
    concepts: ['评估框架', '技术深度', '协作能力', '成长潜力', '面试方法论'],
    relatedPosts: [
      { slug: 'interview-questions', title: '面试我会问的问题', publishedAt: '2026-07-08' },
      { slug: 'remote-work', title: '远程办公实践', publishedAt: '2026-07-10' },
    ],
  },
  'shenzhen-talent-subsidy': {
    title: '深圳人才补贴指南',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-18',
    readingTime: 6,
    toc: [
      { id: 'scope', title: '适用对象', level: 2 },
      { id: 'amount', title: '补贴标准', level: 2 },
      { id: 'process', title: '申请流程', level: 2 },
    ],
    content: `
<p>深圳新引进人才补贴，本科 15000 元/年，分两年发放。</p>
<h2 id="scope">适用对象</h2>
<p>全日制本科及以上学历，首次入户深圳，未享受过同类补贴。</p>
<h2 id="amount">补贴标准</h2>
<p>本科 15000 元/人，硕士 25000 元/人，博士 30000 元/人。</p>
<blockquote>注意：政策可能调整，以深圳市人社局最新公告为准。</blockquote>
<h2 id="process">申请流程</h2>
<p>登录深圳市人社局官网 → 人才服务平台 → 新引进人才补贴 → 在线提交材料。</p>
`,
    concepts: ['新引进人才', '补贴标准', '深圳市人社局', '入户政策'],
    relatedPosts: [
      { slug: 'shenzhen-rent-policy', title: '深圳公租房申请条件', publishedAt: '2026-07-05' },
    ],
  },
  'rag-architecture': {
    title: '我的 RAG 架构选型',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-15',
    readingTime: 12,
    toc: [
      { id: 'why', title: '为什么选 RAG', level: 2 },
      { id: 'stack', title: '技术栈组合', level: 2 },
      { id: 'tradeoffs', title: '取舍', level: 2 },
    ],
    content: `
<p>Milvus + BGE-M3 + reranker，为什么这样组合。</p>
<h2 id="why">为什么选 RAG</h2>
<p>微调成本高、更新慢，RAG 让知识库可以随时增删——对博客场景更合适。</p>
<h2 id="stack">技术栈组合</h2>
<p>向量库 <code>Milvus</code> 负责召回，<code>BGE-M3</code> 做稠密+稀疏混合检索，<code>bge-reranker-v2</code> 二次精排。</p>
<blockquote>reranker 把召回率从 62% 提到 81%，是性价比最高的一环。</blockquote>
<h2 id="tradeoffs">取舍</h2>
<p>Milvus 部署重，但如果只跑单机可以选 <code>qdrant</code>。我选 Milvus 是为了后续水平扩展。</p>
`,
    concepts: ['RAG', 'Milvus', 'BGE-M3', 'bge-reranker-v2', '向量检索', '混合检索'],
    relatedPosts: [
      { slug: 'candidate-eval', title: '候选人评估三维度', publishedAt: '2026-07-20' },
      { slug: 'interview-questions', title: '面试我会问的问题', publishedAt: '2026-07-08' },
    ],
  },
  'remote-work': {
    title: '远程办公实践',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-10',
    readingTime: 10,
    toc: [
      { id: 'async', title: '异步优先', level: 2 },
      { id: 'docs', title: '文档即沟通', level: 2 },
    ],
    content: `
<p>三年远程协作的总结。</p>
<h2 id="async">异步优先</h2>
<p>默认异步沟通，会议是最后手段。能让对方在自己最佳时段处理的事，就不要打断他。</p>
<h2 id="docs">文档即沟通</h2>
<p>重要决策写文档，不要只在会议里说。文档可以搜索、可以回溯、可以让新人快速跟上。</p>
<blockquote>会议结束 10 分钟内发纪要，否则它就消失了。</blockquote>
`,
    concepts: ['异步沟通', '文档协作', '远程办公', '会议纪要'],
    relatedPosts: [
      { slug: 'interview-questions', title: '面试我会问的问题', publishedAt: '2026-07-08' },
      { slug: 'candidate-eval', title: '候选人评估三维度', publishedAt: '2026-07-20' },
    ],
  },
  'interview-questions': {
    title: '面试我会问的问题',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-08',
    readingTime: 5,
    toc: [
      { id: 'framework', title: '三维度框架', level: 2 },
      { id: 'samples', title: '具体问题', level: 2 },
    ],
    content: `
<p>三个维度评估一个人，技术只是其中之一。</p>
<h2 id="framework">三维度框架</h2>
<p>技术深度、协作能力、成长潜力。每个维度 1-5 分，任意一项低于 3 分就不通过。</p>
<h2 id="samples">具体问题</h2>
<p>技术：画一个你最熟悉系统的架构图，然后追问每一层的取舍。</p>
<p>协作：问一个他经历过的冲突，看他描述对方时的措辞。</p>
<p>成长：问他最近半年学的新东西。</p>
`,
    concepts: ['三维度框架', '技术深度', '协作能力', '成长潜力', '面试问题'],
    relatedPosts: [
      { slug: 'candidate-eval', title: '候选人评估三维度', publishedAt: '2026-07-20' },
      { slug: 'remote-work', title: '远程办公实践', publishedAt: '2026-07-10' },
    ],
  },
  'shenzhen-rent-policy': {
    title: '深圳公租房申请条件',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-05',
    readingTime: 7,
    toc: [
      { id: 'threshold', title: '三道门槛', level: 2 },
      { id: 'process', title: '申请流程', level: 2 },
    ],
    content: `
<p>户籍、社保、收入三道门槛，2026 年最新标准。</p>
<h2 id="threshold">三道门槛</h2>
<p>① 深圳户籍 ② 社保连续缴交 3 年 ③ 人均年收入低于 13.3 万元。</p>
<blockquote>轮候库很长，建议入户后尽早申请。</blockquote>
<h2 id="process">申请流程</h2>
<p>登录深圳市住建局 → 住房保障服务 → 公租房轮候申请 → 在线提交材料。</p>
`,
    concepts: ['公租房', '深圳户籍', '社保连续', '收入门槛', '轮候库'],
    relatedPosts: [
      { slug: 'shenzhen-talent-subsidy', title: '深圳人才补贴指南', publishedAt: '2026-07-18' },
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(articles).map((slug) => ({ slug }));
}

export function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Metadata {
  const a = articles[params.slug];
  return { title: a?.title ?? '文章' };
}

export default function ArticlePage({
  params,
}: {
  params: { slug: string };
}) {
  const a = articles[params.slug];
  if (!a) notFound();

  return (
    <ArticleShell
      slug={params.slug}
      article={a}
    />
  );
}
