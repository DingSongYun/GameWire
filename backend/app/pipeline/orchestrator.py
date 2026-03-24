"""内容处理管线编排器"""
import logging

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import Article, ProcessingStatus
from app.pipeline.classify import classify_and_tag
from app.pipeline.cleaning import clean_content
from app.pipeline.dedup import check_duplicate
from app.pipeline.language import detect_language
from app.pipeline.summarize import generate_summary
from app.pipeline.translate import translate_summary_to_zh

logger = logging.getLogger(__name__)


async def process_article(article: Article, session: AsyncSession) -> bool:
    """
    对单篇文章执行完整处理管线：
    清洗 → 去重 → 语言检测 → 摘要 → 分类/标签 → 翻译

    每个阶段完成后更新 processing_status，支持阶段级重试。

    Returns:
        bool: 处理是否成功
    """
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url)
    except Exception:
        logger.warning("Redis 连接失败，token 预算追踪将不可用")

    try:
        # ==================== 阶段 1: 清洗 ====================
        if article.processing_status in (ProcessingStatus.PENDING, ProcessingStatus.CLEANING):
            article.processing_status = ProcessingStatus.CLEANING

            cleaned_text, cleaned_url = clean_content(
                article.content_snippet, article.url
            )
            article.clean_content = cleaned_text
            if cleaned_url:
                article.url = cleaned_url

            await session.flush()
            logger.debug(f"[{article.id}] 清洗完成")

        # ==================== 阶段 2: 去重 ====================
        if article.processing_status in (ProcessingStatus.CLEANING, ProcessingStatus.DEDUP):
            article.processing_status = ProcessingStatus.DEDUP

            content_for_dedup = article.clean_content or article.title
            is_dup, simhash, _ = await check_duplicate(
                article.url, content_for_dedup, session
            )

            if is_dup:
                article.processing_status = ProcessingStatus.DONE
                article.simhash_fingerprint = simhash
                logger.info(f"[{article.id}] 检测到重复，跳过后续处理")
                await session.flush()
                return True

            article.simhash_fingerprint = simhash
            await session.flush()
            logger.debug(f"[{article.id}] 去重通过")

        # ==================== 阶段 3: 语言检测 ====================
        if article.processing_status in (ProcessingStatus.DEDUP, ProcessingStatus.LANGUAGE):
            article.processing_status = ProcessingStatus.LANGUAGE

            text_for_lang = article.clean_content or article.title
            article.language = detect_language(text_for_lang)

            await session.flush()
            logger.debug(f"[{article.id}] 语言: {article.language}")

        # ==================== 阶段 4: 摘要生成 ====================
        if article.processing_status in (ProcessingStatus.LANGUAGE, ProcessingStatus.SUMMARIZING):
            article.processing_status = ProcessingStatus.SUMMARIZING

            content_for_summary = article.clean_content or article.content_snippet or article.title
            summary, tokens = await generate_summary(
                content_for_summary, article.title, redis_client
            )
            article.summary = summary

            await session.flush()
            logger.debug(f"[{article.id}] 摘要生成完成 ({tokens} tokens)")

        # ==================== 阶段 5: 分类/标签 ====================
        if article.processing_status in (ProcessingStatus.SUMMARIZING, ProcessingStatus.CLASSIFYING):
            article.processing_status = ProcessingStatus.CLASSIFYING

            content_for_classify = article.summary or article.clean_content or article.title
            categories, tags = await classify_and_tag(
                article.title, content_for_classify, article.id, session
            )

            await session.flush()
            logger.debug(f"[{article.id}] 分类: {len(categories)}, 标签: {len(tags)}")

        # ==================== 阶段 6: 翻译 ====================
        if article.processing_status in (ProcessingStatus.CLASSIFYING, ProcessingStatus.TRANSLATING):
            article.processing_status = ProcessingStatus.TRANSLATING

            # 如果摘要是英文，翻译为中文
            if article.language == "en" and article.summary:
                article.summary_zh = await translate_summary_to_zh(article.summary)
                await session.flush()
                logger.debug(f"[{article.id}] 翻译完成")

        # ==================== 完成 ====================
        article.processing_status = ProcessingStatus.DONE
        await session.flush()
        logger.info(f"[{article.id}] 处理管线完成")
        return True

    except Exception as e:
        article.processing_status = ProcessingStatus.FAILED
        await session.flush()
        logger.error(f"[{article.id}] 处理管线失败: {e}")
        return False

    finally:
        if redis_client:
            await redis_client.aclose()


async def process_pending_articles(session: AsyncSession, limit: int = 50) -> int:
    """
    批量处理待处理的文章。

    Returns:
        int: 成功处理的文章数
    """
    result = await session.execute(
        select(Article)
        .where(Article.processing_status.in_([
            ProcessingStatus.PENDING,
            ProcessingStatus.CLEANING,
            ProcessingStatus.DEDUP,
            ProcessingStatus.LANGUAGE,
            ProcessingStatus.SUMMARIZING,
            ProcessingStatus.CLASSIFYING,
            ProcessingStatus.TRANSLATING,
        ]))
        .order_by(Article.created_at.asc())
        .limit(limit)
    )
    articles = result.scalars().all()

    if not articles:
        return 0

    success_count = 0
    for article in articles:
        if await process_article(article, session):
            success_count += 1

    logger.info(f"批量处理完成: {success_count}/{len(articles)} 篇成功")
    return success_count
