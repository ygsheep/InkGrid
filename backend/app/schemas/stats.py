"""数据看板统计 schema。"""
from datetime import datetime

from pydantic import BaseModel


class StatsSummary(BaseModel):
    """看板顶部 4 个卡片指标。"""

    postCount: int
    questionCount: int
    knowledgeDocCount: int
    monthlyViews: int


class StatsTrend(BaseModel):
    """近 7 天每日趋势。"""

    posts: list[int]  # 每日新发文章数
    questions: list[int]  # 每日问答次数


class TopArticle(BaseModel):
    """热门文章（按引用次数降序）。"""

    slug: str
    title: str
    channelName: str | None = None
    citationCount: int


class TopQuestion(BaseModel):
    """热门问题（按出现次数降序）。"""

    content: str
    count: int


class RecentQuestion(BaseModel):
    """看板「最近问答」列表项。"""

    sessionId: str
    title: str | None = None
    personaName: str | None = None
    scopeType: str
    scopeRef: str | None = None
    firstQuestion: str | None = None
    lastAnswerSnippet: str | None = None
    messageCount: int
    createdAt: datetime


class StatsOverview(BaseModel):
    """看板聚合响应：单次返回所有看板所需数据。"""

    summary: StatsSummary
    trend: StatsTrend
    topArticles: list[TopArticle]
    topQuestions: list[TopQuestion]
    recentQuestions: list[RecentQuestion]


class QuestionStatItem(BaseModel):
    """问答明细按维度聚合项。"""

    dimension: str
    questionCount: int
    avgLatencyMs: int | None = None
    lastActiveAt: datetime | None = None
