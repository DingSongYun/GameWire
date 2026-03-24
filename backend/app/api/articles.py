"""文章 API 端点"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import (
    Article,
    ArticleCategory,
    ArticleTag,
    Bookmark,
    Category,
    Comment,
    ProcessingStatus,
    ReadStatus,
    Source,
    Tag,
    User,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api", tags=["文章"])


# ==================== Schema ====================


class CategoryBrief(BaseModel):
    id: uuid.UUID
    name: str
    name_zh: Optional[str] = None
    slug: str
    confidence: float = 1.0
    model_config = {"from_attributes": True}


class TagBrief(BaseModel):
    id: uuid.UUID
    canonical_name: str
    model_config = {"from_attributes": True}


class SourceBrief(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    model_config = {"from_attributes": True}


class ArticleListItem(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    summary: Optional[str] = None
    summary_zh: Optional[str] = None
    language: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    source: Optional[SourceBrief] = None
    categories: list[CategoryBrief] = []
    tags: list[TagBrief] = []
    is_bookmarked: bool = False
    is_read: bool = False
    comment_count: int = 0


class ArticleDetail(ArticleListItem):
    content_snippet: Optional[str] = None
    clean_content: Optional[str] = None


class PaginatedArticles(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    per_page: int
    has_next: bool


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: uuid.UUID
    content: str
    user_id: uuid.UUID
    user_name: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ==================== 辅助函数 ====================


def _build_article_item(
    article: Article,
    user_id: uuid.UUID | None = None,
    bookmarked_ids: set | None = None,
    read_ids: set | None = None,
    comment_counts: dict | None = None,
) -> ArticleListItem:
    """构建文章列表项"""
    categories = []
    for ac in article.categories:
        cat = ac.category
        categories.append(CategoryBrief(
            id=cat.id, name=cat.name, name_zh=cat.name_zh,
            slug=cat.slug, confidence=ac.confidence_score,
        ))

    tags = [TagBrief(id=at.tag.id, canonical_name=at.tag.canonical_name) for at in article.tags]

    source = None
    if article.source:
        source = SourceBrief(id=article.source.id, name=article.source.name, type=article.source.type.value)

    return ArticleListItem(
        id=article.id,
        title=article.title,
        url=article.url,
        summary=article.summary,
        summary_zh=article.summary_zh,
        language=article.language,
        author=article.author,
        published_at=article.published_at,
        created_at=article.created_at,
        source=source,
        categories=categories,
        tags=tags,
        is_bookmarked=article.id in (bookmarked_ids or set()),
        is_read=article.id in (read_ids or set()),
        comment_count=(comment_counts or {}).get(article.id, 0),
    )


async def _get_user_context(user_id: uuid.UUID, session: AsyncSession):
    """获取用户的收藏和已读集合"""
    bm_result = await session.execute(
        select(Bookmark.article_id).where(Bookmark.user_id == user_id)
    )
    bookmarked_ids = {row[0] for row in bm_result.all()}

    read_result = await session.execute(
        select(ReadStatus.article_id).where(ReadStatus.user_id == user_id)
    )
    read_ids = {row[0] for row in read_result.all()}

    return bookmarked_ids, read_ids


# ==================== 端点 ====================


@router.get("/articles", response_model=PaginatedArticles)
async def list_articles(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    category_ids: Optional[str] = Query(default=None, description="逗号分隔的分类ID"),
    tag_ids: Optional[str] = Query(default=None, description="逗号分隔的标签ID"),
    source_ids: Optional[str] = Query(default=None, description="逗号分隔的数据源ID"),
    language: Optional[str] = Query(default=None),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文章列表 — 分页、筛选"""
    query = (
        select(Article)
        .where(Article.processing_status == ProcessingStatus.DONE)
        .options(
            selectinload(Article.categories).selectinload(ArticleCategory.category),
            selectinload(Article.tags).selectinload(ArticleTag.tag),
            selectinload(Article.source),
        )
    )

    # 筛选条件
    if category_ids:
        cat_uuids = [uuid.UUID(cid.strip()) for cid in category_ids.split(",") if cid.strip()]
        query = query.join(ArticleCategory).where(ArticleCategory.category_id.in_(cat_uuids))

    if tag_ids:
        tag_uuids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
        query = query.join(ArticleTag).where(ArticleTag.tag_id.in_(tag_uuids))

    if source_ids:
        src_uuids = [uuid.UUID(sid.strip()) for sid in source_ids.split(",") if sid.strip()]
        query = query.where(Article.source_id.in_(src_uuids))

    if language:
        query = query.where(Article.language == language)

    if date_from:
        query = query.where(Article.published_at >= date_from)

    if date_to:
        query = query.where(Article.published_at <= date_to)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.order_by(Article.published_at.desc().nullslast(), Article.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    articles = result.scalars().unique().all()

    # 用户上下文
    bookmarked_ids, read_ids = await _get_user_context(current_user.id, db)

    # 评论计数
    article_ids = [a.id for a in articles]
    cc_result = await db.execute(
        select(Comment.article_id, func.count(Comment.id))
        .where(Comment.article_id.in_(article_ids))
        .group_by(Comment.article_id)
    )
    comment_counts = {row[0]: row[1] for row in cc_result.all()}

    items = [
        _build_article_item(a, current_user.id, bookmarked_ids, read_ids, comment_counts)
        for a in articles
    ]

    return PaginatedArticles(
        items=items, total=total, page=page, per_page=per_page,
        has_next=(page * per_page < total),
    )


@router.get("/articles/search", response_model=PaginatedArticles)
async def search_articles(
    q: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="relevance", pattern="^(relevance|date)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全文搜索文章"""
    # 使用 PostgreSQL tsvector 全文搜索
    ts_query = func.plainto_tsquery("simple", q)
    ts_rank = func.ts_rank(
        func.to_tsvector("simple", func.coalesce(Article.title, "") + " " + func.coalesce(Article.summary, "")),
        ts_query,
    )

    query = (
        select(Article)
        .where(
            Article.processing_status == ProcessingStatus.DONE,
            func.to_tsvector(
                "simple",
                func.coalesce(Article.title, "") + " " + func.coalesce(Article.summary, ""),
            ).op("@@")(ts_query),
        )
        .options(
            selectinload(Article.categories).selectinload(ArticleCategory.category),
            selectinload(Article.tags).selectinload(ArticleTag.tag),
            selectinload(Article.source),
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    if sort == "relevance":
        query = query.order_by(ts_rank.desc())
    else:
        query = query.order_by(Article.published_at.desc().nullslast())

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    articles = result.scalars().unique().all()

    bookmarked_ids, read_ids = await _get_user_context(current_user.id, db)
    article_ids = [a.id for a in articles]
    cc_result = await db.execute(
        select(Comment.article_id, func.count(Comment.id))
        .where(Comment.article_id.in_(article_ids))
        .group_by(Comment.article_id)
    )
    comment_counts = {row[0]: row[1] for row in cc_result.all()}

    items = [
        _build_article_item(a, current_user.id, bookmarked_ids, read_ids, comment_counts)
        for a in articles
    ]

    return PaginatedArticles(
        items=items, total=total, page=page, per_page=per_page,
        has_next=(page * per_page < total),
    )


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文章详情"""
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(
            selectinload(Article.categories).selectinload(ArticleCategory.category),
            selectinload(Article.tags).selectinload(ArticleTag.tag),
            selectinload(Article.source),
        )
    )
    article = result.scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    bookmarked_ids, read_ids = await _get_user_context(current_user.id, db)
    cc_result = await db.execute(
        select(func.count(Comment.id)).where(Comment.article_id == article_id)
    )
    comment_count = cc_result.scalar() or 0

    item = _build_article_item(
        article, current_user.id, bookmarked_ids, read_ids, {article_id: comment_count}
    )
    return ArticleDetail(
        **item.model_dump(),
        content_snippet=article.content_snippet,
        clean_content=article.clean_content,
    )


# ==================== 收藏 ====================


@router.post("/articles/{article_id}/bookmark", status_code=status.HTTP_201_CREATED)
async def bookmark_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收藏文章"""
    existing = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id, Bookmark.article_id == article_id
        )
    )
    if existing.scalar_one_or_none():
        return {"detail": "已收藏"}

    bookmark = Bookmark(id=uuid.uuid4(), user_id=current_user.id, article_id=article_id)
    db.add(bookmark)
    return {"detail": "收藏成功"}


@router.delete("/articles/{article_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消收藏"""
    result = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id, Bookmark.article_id == article_id
        )
    )
    bookmark = result.scalar_one_or_none()
    if bookmark:
        await db.delete(bookmark)


@router.get("/me/bookmarks", response_model=PaginatedArticles)
async def list_bookmarks(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出用户收藏的文章"""
    query = (
        select(Article)
        .join(Bookmark, and_(Bookmark.article_id == Article.id, Bookmark.user_id == current_user.id))
        .options(
            selectinload(Article.categories).selectinload(ArticleCategory.category),
            selectinload(Article.tags).selectinload(ArticleTag.tag),
            selectinload(Article.source),
        )
        .order_by(Bookmark.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    articles = result.scalars().unique().all()

    bookmarked_ids, read_ids = await _get_user_context(current_user.id, db)
    items = [_build_article_item(a, current_user.id, bookmarked_ids, read_ids) for a in articles]

    return PaginatedArticles(
        items=items, total=total, page=page, per_page=per_page,
        has_next=(page * per_page < total),
    )


# ==================== 评论 ====================


@router.post("/articles/{article_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    article_id: uuid.UUID,
    request: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加评论"""
    # 检查文章是否存在
    art = await db.execute(select(Article.id).where(Article.id == article_id))
    if art.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    comment = Comment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        article_id=article_id,
        content=request.content,
    )
    db.add(comment)
    await db.flush()

    return CommentResponse(
        id=comment.id,
        content=comment.content,
        user_id=current_user.id,
        user_name=current_user.display_name,
        created_at=comment.created_at,
    )


@router.get("/articles/{article_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出文章评论"""
    result = await db.execute(
        select(Comment)
        .where(Comment.article_id == article_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()

    return [
        CommentResponse(
            id=c.id, content=c.content, user_id=c.user_id,
            user_name=c.user.display_name, created_at=c.created_at,
        )
        for c in comments
    ]


# ==================== 阅读状态 ====================


@router.post("/articles/{article_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_as_read(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记文章为已读"""
    existing = await db.execute(
        select(ReadStatus).where(
            ReadStatus.user_id == current_user.id, ReadStatus.article_id == article_id
        )
    )
    if existing.scalar_one_or_none() is None:
        rs = ReadStatus(user_id=current_user.id, article_id=article_id)
        db.add(rs)


@router.get("/me/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取未读文章数量"""
    total = await db.execute(
        select(func.count(Article.id)).where(Article.processing_status == ProcessingStatus.DONE)
    )
    total_count = total.scalar() or 0

    read = await db.execute(
        select(func.count(ReadStatus.article_id)).where(ReadStatus.user_id == current_user.id)
    )
    read_count = read.scalar() or 0

    return {"unread_count": max(total_count - read_count, 0)}


# ==================== 翻译 ====================


@router.post("/articles/{article_id}/translate")
async def translate_article(
    article_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按需翻译文章摘要"""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    if not article.summary:
        raise HTTPException(status_code=400, detail="文章无摘要可翻译")

    # 如果已有翻译，直接返回
    if article.summary_zh and article.language == "en":
        return {"summary_zh": article.summary_zh, "cached": True}

    from app.pipeline.translate import translate_summary_to_zh, translate_summary_to_en

    if article.language == "en":
        article.summary_zh = await translate_summary_to_zh(article.summary)
        await db.flush()
        return {"summary_zh": article.summary_zh, "cached": False}
    elif article.language == "zh":
        translated = await translate_summary_to_en(article.summary)
        return {"summary_en": translated, "cached": False}
    else:
        article.summary_zh = await translate_summary_to_zh(article.summary)
        await db.flush()
        return {"summary_zh": article.summary_zh, "cached": False}
