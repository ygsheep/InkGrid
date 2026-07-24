"""Q&A 审核相关 schema。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QaPairOut(BaseModel):
    """Q&A 输出。"""

    model_config = {"from_attributes": True}

    id: UUID
    article_id: UUID
    question: str
    answer: str
    status: str
    milvus_chunk_id: str | None = None
    created_at: datetime
    updated_at: datetime
    article_title: str | None = None


class QaPairOutWithArticle(QaPairOut):
    """带文章标题的 Q&A 输出（审核列表用）。"""

    article_title: str | None = None
    article_slug: str | None = None


class QaReviewIn(BaseModel):
    """审核操作输入。"""

    status: str = Field(..., description="approved | rejected")
    question: str | None = Field(None, description="修改后的问题")
    answer: str | None = Field(None, description="修改后的答案")
