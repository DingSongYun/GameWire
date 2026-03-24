"""趋势分析 API — 趋势话题、时间序列、对比、分类分布"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import get_current_user
from app.models.models import TrendDigest
from app.services.digest import generate_weekly_digest
from app.services.trends import (
    detect_rising_trends,
    get_category_distribution,
    get_tag_timeseries,
    get_tags_comparison,
)

router = APIRouter(prefix="/api/trends", tags=["趋势分析"])


@router.get("/topics")
async def trending_topics(
    window_days: int = Query(7, ge=1, le=90, description="对比窗口天数"),
    growth_threshold: float = Query(0.5, ge=0, description="增长阈值（0.5=50%）"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回前 N 个趋势话题，包含增长率、当前数量、上期数量。
    """
    topics = await detect_rising_trends(
        window_days=window_days,
        growth_threshold=growth_threshold,
        limit=limit,
        session=db,
    )
    return {
        "window_days": window_days,
        "growth_threshold": growth_threshold,
        "topics": topics,
        "total": len(topics),
    }


@router.get("/topic/{tag_id}/timeseries")
async def topic_timeseries(
    tag_id: uuid.UUID,
    days: int = Query(30, ge=7, le=90, description="时间范围（7/30/90天）"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回指定标签在所选时间范围内的每日文章数量。
    """
    series = await get_tag_timeseries(tag_id=tag_id, days=days, session=db)
    return {
        "tag_id": str(tag_id),
        "days": days,
        "data": series,
    }


@router.get("/compare")
async def compare_topics(
    tag_ids: str = Query(..., description="逗号分隔的标签 ID（2-5个）"),
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回 2-5 个标签的叠加时间序列用于对比。
    """
    try:
        ids = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="tag_ids 格式无效，请使用逗号分隔的 UUID")

    if len(ids) < 2 or len(ids) > 5:
        raise HTTPException(status_code=400, detail="请提供 2-5 个标签 ID 进行对比")

    result = await get_tags_comparison(tag_ids=ids, days=days, session=db)
    return {
        "days": days,
        **result,
    }


@router.get("/distribution")
async def category_distribution(
    days: int = Query(7, ge=1, le=90, description="时间范围天数"),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回指定时间段内的分类分布（文章数量和百分比）。
    """
    dist = await get_category_distribution(days=days, session=db)
    return {
        "days": days,
        "categories": dist,
    }


# ==================== 每周摘要 API ====================


@router.get("/digests")
async def list_digests(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    列出每周趋势摘要，按时间倒序。
    """
    from sqlalchemy import select

    stmt = (
        select(TrendDigest)
        .order_by(TrendDigest.week_start.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    digests = result.scalars().all()

    return {
        "digests": [
            {
                "id": str(d.id),
                "week_start": d.week_start.isoformat(),
                "content": d.content,
                "generated_at": d.generated_at.isoformat() if d.generated_at else None,
            }
            for d in digests
        ],
        "total": len(digests),
    }


@router.get("/digests/latest")
async def latest_digest(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    返回最新的每周摘要。包含 is_new 标识（7天内生成的视为"新"）。
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select

    stmt = (
        select(TrendDigest)
        .order_by(TrendDigest.week_start.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    digest = result.scalar_one_or_none()

    if digest is None:
        return {"digest": None, "is_new": False}

    now = datetime.now(timezone.utc)
    is_new = (
        digest.generated_at is not None
        and (now - digest.generated_at.replace(tzinfo=timezone.utc)).days < 7
    )

    return {
        "digest": {
            "id": str(digest.id),
            "week_start": digest.week_start.isoformat(),
            "content": digest.content,
            "generated_at": digest.generated_at.isoformat() if digest.generated_at else None,
        },
        "is_new": is_new,
    }
