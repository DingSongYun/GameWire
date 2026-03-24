"""分类与标签 API 端点"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import (
    ArticleCategory,
    ArticleTag,
    Category,
    Tag,
    User,
)
from app.services.auth import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["分类与标签"])
admin_router = APIRouter(prefix="/api/admin", tags=["分类管理"])


# ==================== Schema ====================


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    name_zh: Optional[str] = None
    slug: str
    is_active: bool
    display_order: int
    article_count: int = 0
    model_config = {"from_attributes": True}


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    name_zh: Optional[str] = None
    slug: str = Field(min_length=1, max_length=255)
    display_order: int = 0


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    name_zh: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class TagResponse(BaseModel):
    id: uuid.UUID
    canonical_name: str
    article_count: int = 0
    model_config = {"from_attributes": True}


class TagCloudItem(BaseModel):
    id: uuid.UUID
    canonical_name: str
    count: int
    weight: float  # 0.0 - 1.0 归一化权重


# ==================== 分类端点 ====================


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """列出所有激活的分类及文章数量"""
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.display_order)  # noqa: E712
    )
    categories = result.scalars().all()

    response = []
    for cat in categories:
        count_result = await db.execute(
            select(func.count(ArticleCategory.article_id))
            .where(ArticleCategory.category_id == cat.id)
        )
        article_count = count_result.scalar() or 0
        response.append(CategoryResponse(
            id=cat.id, name=cat.name, name_zh=cat.name_zh, slug=cat.slug,
            is_active=cat.is_active, display_order=cat.display_order,
            article_count=article_count,
        ))

    return response


@admin_router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """添加新分类（仅管理员）"""
    # 检查 slug 唯一性
    existing = await db.execute(select(Category).where(Category.slug == request.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="分类 slug 已存在")

    category = Category(
        id=uuid.uuid4(),
        name=request.name,
        name_zh=request.name_zh,
        slug=request.slug,
        display_order=request.display_order,
        is_active=True,
    )
    db.add(category)
    await db.flush()

    return CategoryResponse(
        id=category.id, name=category.name, name_zh=category.name_zh,
        slug=category.slug, is_active=True, display_order=category.display_order,
        article_count=0,
    )


@admin_router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    request: CategoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """重命名或禁用分类（仅管理员）"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    if request.name is not None:
        category.name = request.name
    if request.name_zh is not None:
        category.name_zh = request.name_zh
    if request.is_active is not None:
        category.is_active = request.is_active
    if request.display_order is not None:
        category.display_order = request.display_order

    await db.flush()

    count_result = await db.execute(
        select(func.count(ArticleCategory.article_id)).where(ArticleCategory.category_id == category.id)
    )
    article_count = count_result.scalar() or 0

    return CategoryResponse(
        id=category.id, name=category.name, name_zh=category.name_zh,
        slug=category.slug, is_active=category.is_active,
        display_order=category.display_order, article_count=article_count,
    )


# ==================== 标签端点 ====================


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """按频率排序列出标签"""
    result = await db.execute(
        select(Tag, func.count(ArticleTag.article_id).label("cnt"))
        .outerjoin(ArticleTag, ArticleTag.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(func.count(ArticleTag.article_id).desc())
        .limit(limit)
    )
    rows = result.all()

    return [
        TagResponse(id=tag.id, canonical_name=tag.canonical_name, article_count=cnt)
        for tag, cnt in rows
    ]


@router.get("/tags/cloud", response_model=list[TagCloudItem])
async def get_tag_cloud(
    n: int = Query(default=30, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """返回前 N 个标签及频率权重，用于标签云渲染"""
    result = await db.execute(
        select(Tag, func.count(ArticleTag.article_id).label("cnt"))
        .outerjoin(ArticleTag, ArticleTag.tag_id == Tag.id)
        .group_by(Tag.id)
        .having(func.count(ArticleTag.article_id) > 0)
        .order_by(func.count(ArticleTag.article_id).desc())
        .limit(n)
    )
    rows = result.all()

    if not rows:
        return []

    max_count = max(cnt for _, cnt in rows)
    min_count = min(cnt for _, cnt in rows)
    range_count = max(max_count - min_count, 1)

    return [
        TagCloudItem(
            id=tag.id,
            canonical_name=tag.canonical_name,
            count=cnt,
            weight=round((cnt - min_count) / range_count, 2),
        )
        for tag, cnt in rows
    ]
