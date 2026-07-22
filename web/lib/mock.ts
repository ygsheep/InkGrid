import type { ArticleSummary, Channel, Persona } from '@/types';

/** 骨架阶段 mock 数据，接后端后替换为 API */
export const mockPosts: ArticleSummary[] = [
  {
    id: '1',
    slug: 'candidate-eval',
    title: '候选人评估三维度',
    excerpt: '技术深度、协作能力、成长潜力，我这样给候选人打分',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-20',
    readingTime: 8,
  },
  {
    id: '2',
    slug: 'shenzhen-talent-subsidy',
    title: '深圳人才补贴指南',
    excerpt: '本科 15000 元/年，新引进人才补贴申请全流程',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-18',
    readingTime: 6,
  },
  {
    id: '3',
    slug: 'remote-work',
    title: '远程办公实践',
    excerpt: '我倾向于异步沟通，这是三年远程协作的总结',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-15',
    readingTime: 10,
  },
  {
    id: '4',
    slug: 'interview-questions',
    title: '面试我会问的问题',
    excerpt: '三个维度评估一个人，技术只是其中之一',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-10',
    readingTime: 5,
  },
  {
    id: '5',
    slug: 'shenzhen-rent-policy',
    title: '深圳公租房申请条件',
    excerpt: '户籍、社保、收入三道门槛，2026 年最新标准',
    channel: 'policy',
    channelName: '政策',
    publishedAt: '2026-07-08',
    readingTime: 7,
  },
  {
    id: '6',
    slug: 'rag-architecture',
    title: '我的 RAG 架构选型',
    excerpt: 'Milvus + BGE-M3 + reranker，为什么这样组合',
    channel: 'channel',
    channelName: '经验',
    publishedAt: '2026-07-05',
    readingTime: 12,
  },
];

export const mockChannels: Channel[] = [
  {
    slug: 'channel',
    name: '个人经验',
    description: '记录招聘、协作、工程经验。HR 可直接问 AI，它用我的口吻代答。',
    accent: 'channel',
    postCount: 4,
  },
  {
    slug: 'policy',
    name: '深圳政策',
    description: '深圳人才、住房、补贴等政策查询与法律规范。',
    accent: 'policy',
    postCount: 2,
  },
];

/** AI 对话角色列表 */
export const mockPersonas: Persona[] = [
  {
    id: 'author',
    serial: '001',
    name: '博客作者',
    tagline: '博主本人',
    description: '基于博主已发表的文章回答提问，保持作者本人的口吻、立场与技术判断。',
    tags: ['说明性', '技术性', '基于知识库'],
  },
  {
    id: 'mentor',
    serial: '002',
    name: '职业导师',
    tagline: '面试与成长',
    description: '聚焦招聘评估、协作模式与职业成长路径，给出可执行的判断框架。',
    tags: ['建议性', '经验驱动'],
  },
  {
    id: 'policy-advisor',
    serial: '003',
    name: '政策顾问',
    tagline: '深圳政策专员',
    description: '解读深圳人才补贴、住房、社保等政策，给出申请条件与流程指引。',
    tags: ['规范性', '流程化'],
  },
];

/** 默认角色 id */
export const DEFAULT_PERSONA_ID = 'author';
