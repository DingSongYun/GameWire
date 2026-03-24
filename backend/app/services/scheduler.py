"""集中式采集调度器 — 使用 APScheduler 独立调度每个数据源"""
import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import RawArticle
from app.adapters.registry import get_adapter
from app.database import async_session
from app.models.models import (
    Article,
    CollectionLog,
    CollectionStatus,
    ProcessingStatus,
    Source,
    SourceStatus,
)

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = AsyncIOScheduler()

# 最小采集间隔（分钟）
MIN_INTERVAL_MINUTES = 15

# 连续失败降级阈值
DEGRADED_THRESHOLD = 5

# 最大重试次数
MAX_RETRIES = 3


async def collect_from_source(source_id: str) -> None:
    """执行单个数据源的采集任务"""
    async with async_session() as session:
        # 加载数据源配置
        result = await session.execute(
            select(Source).where(Source.id == uuid.UUID(source_id))
        )
        source = result.scalar_one_or_none()

        if source is None or not source.is_enabled:
            logger.debug(f"数据源 {source_id} 不存在或已禁用，跳过")
            return

        if source.status == SourceStatus.DISABLED:
            return

        # 创建采集日志
        log_entry = CollectionLog(
            id=uuid.uuid4(),
            source_id=source.id,
            started_at=datetime.now(timezone.utc),
            articles_fetched=0,
            status=CollectionStatus.SUCCESS,
        )

        retries = 0
        last_error = None

        while retries <= MAX_RETRIES:
            try:
                # 获取适配器并抓取
                adapter = get_adapter(source.type, source.config)
                raw_articles: list[RawArticle] = await adapter.fetch()

                # 存储文章
                saved_count = 0
                for raw in raw_articles:
                    # 检查 URL 是否已存在（URL 去重）
                    existing = await session.execute(
                        select(Article.id).where(Article.url == raw.url)
                    )
                    if existing.scalar_one_or_none() is not None:
                        continue

                    article = Article(
                        id=uuid.uuid4(),
                        url=raw.url,
                        title=raw.title,
                        content_snippet=raw.content_snippet,
                        author=raw.author,
                        published_at=raw.published_at,
                        source_id=source.id,
                        processing_status=ProcessingStatus.PENDING,
                        raw_metadata=raw.raw_metadata,
                    )
                    session.add(article)
                    saved_count += 1

                # 更新数据源状态 — 成功
                source.last_collected_at = datetime.now(timezone.utc)
                source.consecutive_failures = 0
                if source.status == SourceStatus.DEGRADED:
                    source.status = SourceStatus.ACTIVE

                # 更新日志
                log_entry.articles_fetched = saved_count
                log_entry.completed_at = datetime.now(timezone.utc)
                log_entry.status = CollectionStatus.SUCCESS

                logger.info(
                    f"数据源 [{source.name}] 采集完成: 抓取 {len(raw_articles)} 篇, 新增 {saved_count} 篇"
                )

                # 触发管线处理新文章
                if saved_count > 0:
                    from app.pipeline.orchestrator import process_pending_articles
                    processed = await process_pending_articles(session, limit=saved_count)
                    logger.info(f"管线处理完成: {processed}/{saved_count} 篇")

                break  # 成功，跳出重试循环

            except Exception as e:
                retries += 1
                last_error = str(e)
                logger.warning(
                    f"数据源 [{source.name}] 采集失败 (重试 {retries}/{MAX_RETRIES}): {e}"
                )

                if retries <= MAX_RETRIES:
                    # 指数退避等待
                    import asyncio
                    wait_seconds = 2 ** retries * 5  # 10s, 20s, 40s
                    await asyncio.sleep(wait_seconds)
                else:
                    # 重试耗尽
                    source.consecutive_failures += 1

                    # 健康追踪：连续 5 次失败标记为降级
                    if source.consecutive_failures >= DEGRADED_THRESHOLD:
                        source.status = SourceStatus.DEGRADED
                        logger.warning(
                            f"数据源 [{source.name}] 连续 {source.consecutive_failures} 次失败，标记为降级"
                        )

                    log_entry.completed_at = datetime.now(timezone.utc)
                    log_entry.status = CollectionStatus.FAILED
                    log_entry.error_message = last_error

        session.add(log_entry)
        await session.commit()


async def load_and_schedule_sources() -> None:
    """从数据库加载所有启用的数据源，注册到调度器"""
    async with async_session() as session:
        result = await session.execute(
            select(Source).where(Source.is_enabled == True)  # noqa: E712
        )
        sources = result.scalars().all()

        for source in sources:
            interval = max(source.cron_interval, MIN_INTERVAL_MINUTES)
            job_id = f"collect_{source.id}"

            # 避免重复注册
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            scheduler.add_job(
                collect_from_source,
                "interval",
                minutes=interval,
                id=job_id,
                args=[str(source.id)],
                replace_existing=True,
                max_instances=1,
            )
            logger.info(f"已调度数据源 [{source.name}] 每 {interval} 分钟采集一次")

    logger.info(f"调度器加载完成，共 {len(sources)} 个数据源")


def validate_interval(interval: int) -> int:
    """验证并强制执行最小采集间隔"""
    if interval < MIN_INTERVAL_MINUTES:
        raise ValueError(
            f"采集间隔不能低于 {MIN_INTERVAL_MINUTES} 分钟，当前值: {interval}"
        )
    return interval


async def start_scheduler() -> None:
    """启动调度器"""
    await load_and_schedule_sources()

    # ── 每日频率聚合任务（每天凌晨 2:00 运行）──
    from app.services.trends import run_daily_aggregation_job

    scheduler.add_job(
        run_daily_aggregation_job,
        "cron",
        hour=2,
        minute=0,
        id="daily_frequency_aggregation",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("已调度每日频率聚合任务: 每天 02:00")

    # ── 每周摘要生成任务（每周一 9:00 运行）──
    from app.services.digest import run_weekly_digest_job

    scheduler.add_job(
        run_weekly_digest_job,
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_digest_generation",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("已调度每周摘要生成任务: 每周一 09:00")

    scheduler.start()
    logger.info("采集调度器已启动")


async def stop_scheduler() -> None:
    """停止调度器"""
    scheduler.shutdown(wait=False)
    logger.info("采集调度器已停止")


async def refresh_source_schedule(source_id: uuid.UUID) -> None:
    """刷新单个数据源的调度（配置更新后调用）"""
    async with async_session() as session:
        result = await session.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()

        job_id = f"collect_{source_id}"

        if source is None or not source.is_enabled:
            # 移除已禁用的调度
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            return

        interval = max(source.cron_interval, MIN_INTERVAL_MINUTES)
        scheduler.add_job(
            collect_from_source,
            "interval",
            minutes=interval,
            id=job_id,
            args=[str(source.id)],
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f"已刷新数据源 [{source.name}] 调度: 每 {interval} 分钟")
