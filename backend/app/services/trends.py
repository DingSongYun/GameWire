"""趋势分析引擎 — 频率聚合与上升趋势检测"""

import logging
import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.models import (
    Article,
    ArticleCategory,
    ArticleTag,
    Category,
    ProcessingStatus,
    Tag,
    TagFrequency,
)

logger = logging.getLogger(__name__)

# 趋势检测默认增长阈值（50%）
DEFAULT_GROWTH_THRESHOLD = 0.5

# 趋势对比窗口（天）
TREND_WINDOW_DAYS = 7


async def aggregate_daily_frequencies(
    target_date: Optional[date] = None,
    session: Optional[AsyncSession] = None,
) -> int:
    """
    每日频率聚合任务：按天统计每个标签（可选按分类细分）的文章数量，写入 TagFrequency。

    Args:
        target_date: 要统计的日期，默认为昨天
        session: 可选的外部 session

    Returns:
        写入的频率记录数
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    async def _run(sess: AsyncSession) -> int:
        # 先删除该日期已有的聚合数据（幂等）
        await sess.execute(
            delete(TagFrequency).where(TagFrequency.date == target_date)
        )

        # ─── 1. 按标签聚合（不区分分类，category_id = NULL）───
        tag_counts_stmt = (
            select(
                ArticleTag.tag_id,
                func.count(ArticleTag.article_id).label("cnt"),
            )
            .join(Article, Article.id == ArticleTag.article_id)
            .where(
                and_(
                    func.date(Article.published_at) == target_date,
                    Article.processing_status == ProcessingStatus.DONE,
                )
            )
            .group_by(ArticleTag.tag_id)
        )
        tag_rows = (await sess.execute(tag_counts_stmt)).all()

        written = 0
        for tag_id, cnt in tag_rows:
            freq = TagFrequency(
                id=uuid.uuid4(),
                tag_id=tag_id,
                category_id=None,
                date=target_date,
                count=cnt,
            )
            sess.add(freq)
            written += 1

        # ─── 2. 按标签 × 分类 交叉聚合 ───
        cross_stmt = (
            select(
                ArticleTag.tag_id,
                ArticleCategory.category_id,
                func.count(Article.id).label("cnt"),
            )
            .select_from(Article)
            .join(ArticleTag, Article.id == ArticleTag.article_id)
            .join(ArticleCategory, Article.id == ArticleCategory.article_id)
            .where(
                and_(
                    func.date(Article.published_at) == target_date,
                    Article.processing_status == ProcessingStatus.DONE,
                )
            )
            .group_by(ArticleTag.tag_id, ArticleCategory.category_id)
        )
        cross_rows = (await sess.execute(cross_stmt)).all()

        for tag_id, category_id, cnt in cross_rows:
            freq = TagFrequency(
                id=uuid.uuid4(),
                tag_id=tag_id,
                category_id=category_id,
                date=target_date,
                count=cnt,
            )
            sess.add(freq)
            written += 1

        await sess.flush()
        logger.info(
            f"每日频率聚合完成 [{target_date}]: 写入 {written} 条记录 "
            f"(标签级 {len(tag_rows)}, 交叉级 {len(cross_rows)})"
        )
        return written

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            result = await _run(sess)
            await sess.commit()
            return result


async def detect_rising_trends(
    window_days: int = TREND_WINDOW_DAYS,
    growth_threshold: float = DEFAULT_GROWTH_THRESHOLD,
    limit: int = 20,
    session: Optional[AsyncSession] = None,
) -> list[dict]:
    """
    上升趋势检测：比较当前周期与上一周期的频率，找出增长超过阈值的话题。

    Args:
        window_days: 对比窗口天数（默认7天）
        growth_threshold: 增长阈值（默认0.5 = 50%）
        limit: 返回前 N 个趋势话题
        session: 可选的外部 session

    Returns:
        按增长率降序排列的趋势话题列表
    """
    today = date.today()
    current_start = today - timedelta(days=window_days)
    prev_start = current_start - timedelta(days=window_days)

    async def _run(sess: AsyncSession) -> list[dict]:
        # 当前周期各标签的文章总数（只看 category_id IS NULL 的聚合行）
        current_stmt = (
            select(
                TagFrequency.tag_id,
                func.sum(TagFrequency.count).label("current_count"),
            )
            .where(
                and_(
                    TagFrequency.date >= current_start,
                    TagFrequency.date < today,
                    TagFrequency.category_id.is_(None),
                )
            )
            .group_by(TagFrequency.tag_id)
        )
        current_rows = {r.tag_id: r.current_count for r in (await sess.execute(current_stmt)).all()}

        # 上一周期各标签的文章总数
        prev_stmt = (
            select(
                TagFrequency.tag_id,
                func.sum(TagFrequency.count).label("prev_count"),
            )
            .where(
                and_(
                    TagFrequency.date >= prev_start,
                    TagFrequency.date < current_start,
                    TagFrequency.category_id.is_(None),
                )
            )
            .group_by(TagFrequency.tag_id)
        )
        prev_rows = {r.tag_id: r.prev_count for r in (await sess.execute(prev_stmt)).all()}

        # 计算增长率
        trends = []
        all_tag_ids = set(current_rows.keys()) | set(prev_rows.keys())

        for tag_id in all_tag_ids:
            current = current_rows.get(tag_id, 0)
            prev = prev_rows.get(tag_id, 0)

            if current == 0:
                continue  # 当前周期无数据，不算趋势

            if prev == 0:
                # 上期为 0，本期有数据 → 新话题，视为无穷增长，用特殊值
                growth_rate = float(current)  # 数值本身作为"权重"
                is_new = True
            else:
                growth_rate = (current - prev) / prev
                is_new = False

            if growth_rate >= growth_threshold:
                trends.append({
                    "tag_id": str(tag_id),
                    "current_count": int(current),
                    "previous_count": int(prev),
                    "growth_rate": round(growth_rate, 4),
                    "is_new_topic": is_new,
                })

        # 按增长率降序排列
        trends.sort(key=lambda x: x["growth_rate"], reverse=True)

        # 填充标签名称
        if trends:
            tag_ids = [uuid.UUID(t["tag_id"]) for t in trends[:limit]]
            tag_result = await sess.execute(
                select(Tag.id, Tag.canonical_name).where(Tag.id.in_(tag_ids))
            )
            tag_names = {str(r.id): r.canonical_name for r in tag_result.all()}
            for t in trends[:limit]:
                t["tag_name"] = tag_names.get(t["tag_id"], "unknown")

        return trends[:limit]

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            return await _run(sess)


async def get_tag_timeseries(
    tag_id: uuid.UUID,
    days: int = 30,
    session: Optional[AsyncSession] = None,
) -> list[dict]:
    """
    获取指定标签的每日文章数量时间序列。

    Args:
        tag_id: 标签 ID
        days: 时间范围（7/30/90）
        session: 可选的外部 session

    Returns:
        按日期升序的 [{date, count}] 列表
    """
    start_date = date.today() - timedelta(days=days)

    async def _run(sess: AsyncSession) -> list[dict]:
        stmt = (
            select(TagFrequency.date, TagFrequency.count)
            .where(
                and_(
                    TagFrequency.tag_id == tag_id,
                    TagFrequency.category_id.is_(None),
                    TagFrequency.date >= start_date,
                )
            )
            .order_by(TagFrequency.date.asc())
        )
        rows = (await sess.execute(stmt)).all()
        return [{"date": r.date.isoformat(), "count": r.count} for r in rows]

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            return await _run(sess)


async def get_tags_comparison(
    tag_ids: list[uuid.UUID],
    days: int = 30,
    session: Optional[AsyncSession] = None,
) -> dict[str, list[dict]]:
    """
    获取 2-5 个标签的叠加时间序列，用于对比。

    Args:
        tag_ids: 2-5 个标签的 ID
        days: 时间范围
        session: 可选的外部 session

    Returns:
        {tag_id: [{date, count}]} 字典
    """
    start_date = date.today() - timedelta(days=days)

    async def _run(sess: AsyncSession) -> dict[str, list[dict]]:
        stmt = (
            select(TagFrequency.tag_id, TagFrequency.date, TagFrequency.count)
            .where(
                and_(
                    TagFrequency.tag_id.in_(tag_ids),
                    TagFrequency.category_id.is_(None),
                    TagFrequency.date >= start_date,
                )
            )
            .order_by(TagFrequency.tag_id, TagFrequency.date.asc())
        )
        rows = (await sess.execute(stmt)).all()

        result: dict[str, list[dict]] = {str(tid): [] for tid in tag_ids}
        for r in rows:
            result[str(r.tag_id)].append({
                "date": r.date.isoformat(),
                "count": r.count,
            })

        # 填充标签名称
        tag_result = await sess.execute(
            select(Tag.id, Tag.canonical_name).where(Tag.id.in_(tag_ids))
        )
        tag_names = {str(r.id): r.canonical_name for r in tag_result.all()}

        return {
            "series": result,
            "tag_names": tag_names,
        }

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            return await _run(sess)


async def get_category_distribution(
    days: int = 7,
    session: Optional[AsyncSession] = None,
) -> list[dict]:
    """
    获取指定时间段内文章在各分类中的分布。

    Args:
        days: 时间范围（天数）
        session: 可选的外部 session

    Returns:
        [{category_id, category_name, count, percentage}] 列表
    """
    start_date = date.today() - timedelta(days=days)

    async def _run(sess: AsyncSession) -> list[dict]:
        stmt = (
            select(
                ArticleCategory.category_id,
                Category.name,
                Category.name_zh,
                func.count(ArticleCategory.article_id).label("cnt"),
            )
            .join(Category, Category.id == ArticleCategory.category_id)
            .join(Article, Article.id == ArticleCategory.article_id)
            .where(
                and_(
                    func.date(Article.published_at) >= start_date,
                    Article.processing_status == ProcessingStatus.DONE,
                )
            )
            .group_by(ArticleCategory.category_id, Category.name, Category.name_zh)
            .order_by(func.count(ArticleCategory.article_id).desc())
        )
        rows = (await sess.execute(stmt)).all()

        total = sum(r.cnt for r in rows) or 1
        return [
            {
                "category_id": str(r.category_id),
                "category_name": r.name,
                "category_name_zh": r.name_zh,
                "count": r.cnt,
                "percentage": round(r.cnt / total * 100, 2),
            }
            for r in rows
        ]

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            return await _run(sess)


async def run_daily_aggregation_job() -> None:
    """供调度器调用的每日聚合入口"""
    try:
        count = await aggregate_daily_frequencies()
        logger.info(f"每日聚合调度任务完成，写入 {count} 条记录")
    except Exception as e:
        logger.error(f"每日聚合调度任务失败: {e}")
