"""数据源管理 API 端点"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Article, CollectionLog, Source, SourceStatus, SourceType, User
from app.services.auth import require_admin

router = APIRouter(prefix="/api/admin/sources", tags=["数据源管理"])


# ==================== Schema ====================


class SourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: SourceType
    config: dict = Field(default_factory=dict)
    cron_interval: int = Field(default=30, ge=15)  # 最低 15 分钟


class SourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    cron_interval: Optional[int] = Field(default=None, ge=15)
    is_enabled: Optional[bool] = None


class SourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    config: dict
    cron_interval: int
    is_enabled: bool
    status: str
    last_collected_at: Optional[str] = None
    consecutive_failures: int
    article_count: int = 0

    model_config = {"from_attributes": True}


class CollectionLogResponse(BaseModel):
    id: uuid.UUID
    started_at: str
    completed_at: Optional[str] = None
    articles_fetched: int
    status: str
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ==================== 端点 ====================


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出所有数据源"""
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    sources = result.scalars().all()

    response = []
    for source in sources:
        # 统计文章数量
        count_result = await db.execute(
            select(func.count(Article.id)).where(Article.source_id == source.id)
        )
        article_count = count_result.scalar() or 0

        response.append(
            SourceResponse(
                id=source.id,
                name=source.name,
                type=source.type.value,
                config=source.config,
                cron_interval=source.cron_interval,
                is_enabled=source.is_enabled,
                status=source.status.value,
                last_collected_at=source.last_collected_at.isoformat() if source.last_collected_at else None,
                consecutive_failures=source.consecutive_failures,
                article_count=article_count,
            )
        )

    return response


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    request: SourceCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """创建新数据源"""
    source = Source(
        id=uuid.uuid4(),
        name=request.name,
        type=request.type,
        config=request.config,
        cron_interval=request.cron_interval,
        is_enabled=True,
        status=SourceStatus.ACTIVE,
        consecutive_failures=0,
    )
    db.add(source)
    await db.flush()

    return SourceResponse(
        id=source.id,
        name=source.name,
        type=source.type.value,
        config=source.config,
        cron_interval=source.cron_interval,
        is_enabled=source.is_enabled,
        status=source.status.value,
        last_collected_at=None,
        consecutive_failures=0,
        article_count=0,
    )


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: uuid.UUID,
    request: SourceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """更新数据源配置"""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")

    if request.name is not None:
        source.name = request.name
    if request.config is not None:
        source.config = request.config
    if request.cron_interval is not None:
        source.cron_interval = request.cron_interval
    if request.is_enabled is not None:
        source.is_enabled = request.is_enabled

    await db.flush()

    count_result = await db.execute(
        select(func.count(Article.id)).where(Article.source_id == source.id)
    )
    article_count = count_result.scalar() or 0

    return SourceResponse(
        id=source.id,
        name=source.name,
        type=source.type.value,
        config=source.config,
        cron_interval=source.cron_interval,
        is_enabled=source.is_enabled,
        status=source.status.value,
        last_collected_at=source.last_collected_at.isoformat() if source.last_collected_at else None,
        consecutive_failures=source.consecutive_failures,
        article_count=article_count,
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """删除数据源"""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")

    await db.delete(source)


@router.get("/{source_id}/logs", response_model=list[CollectionLogResponse])
async def get_source_logs(
    source_id: uuid.UUID,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """获取数据源的采集历史"""
    # 检查数据源是否存在
    source_result = await db.execute(select(Source).where(Source.id == source_id))
    if source_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据源不存在")

    result = await db.execute(
        select(CollectionLog)
        .where(CollectionLog.source_id == source_id)
        .order_by(CollectionLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        CollectionLogResponse(
            id=log.id,
            started_at=log.started_at.isoformat(),
            completed_at=log.completed_at.isoformat() if log.completed_at else None,
            articles_fetched=log.articles_fetched,
            status=log.status.value,
            error_message=log.error_message,
        )
        for log in logs
    ]
