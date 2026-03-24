"""每周趋势摘要生成 — 使用 LLM 总结本周趋势"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.models import TrendDigest
from app.services.trends import (
    detect_rising_trends,
    get_category_distribution,
)

logger = logging.getLogger(__name__)


async def generate_weekly_digest(
    session: Optional[AsyncSession] = None,
) -> Optional[TrendDigest]:
    """
    生成每周趋势摘要：
    1. 获取本周趋势话题
    2. 获取分类分布
    3. 调用 LLM 生成自然语言总结
    4. 存入 TrendDigest 表
    """
    # 计算本周起始日期（上周一）
    today = date.today()
    week_start = today - timedelta(days=today.weekday() + 7)  # 上周一

    async def _run(sess: AsyncSession) -> Optional[TrendDigest]:
        # 检查是否已存在本周摘要（幂等）
        existing = await sess.execute(
            select(TrendDigest).where(TrendDigest.week_start == week_start)
        )
        if existing.scalar_one_or_none() is not None:
            logger.info(f"本周摘要已存在 [{week_start}]，跳过生成")
            return None

        # 获取趋势数据
        trends = await detect_rising_trends(
            window_days=7,
            growth_threshold=0.3,  # 稍低阈值以涵盖更多话题
            limit=20,
            session=sess,
        )
        distribution = await get_category_distribution(days=7, session=sess)

        # 构建 LLM 提示
        trends_text = _format_trends_for_prompt(trends)
        dist_text = _format_distribution_for_prompt(distribution)

        prompt = f"""你是一位游戏行业和 AI 技术领域的资深分析师。请基于以下数据，生成一份简洁、专业的每周趋势摘要报告。

## 本周趋势话题数据
{trends_text}

## 本周分类分布数据
{dist_text}

## 报告周期
{week_start} 至 {week_start + timedelta(days=6)}

## 输出要求
请用中文撰写，包含以下部分：
1. **本周概览**（2-3 句话总结本周要点）
2. **热门趋势**（列出 3-5 个最显著的趋势话题，说明其增长原因和影响）
3. **新兴话题**（列出本周新出现的话题，简要说明）
4. **分类动态**（各分类的文章分布变化）
5. **展望**（下周值得关注的方向）

请保持专业但易读的语气，适合游戏公司技术团队阅读。"""

        # 调用 LLM 生成摘要
        try:
            content = await _call_llm_for_digest(prompt)
        except Exception as e:
            logger.error(f"LLM 生成每周摘要失败: {e}")
            # 降级：使用结构化数据生成简要摘要
            content = _generate_fallback_digest(trends, distribution, week_start)

        # 存储摘要
        digest = TrendDigest(
            id=uuid.uuid4(),
            week_start=week_start,
            content=content,
            generated_at=datetime.now(timezone.utc),
        )
        sess.add(digest)
        await sess.flush()

        logger.info(f"每周摘要生成完成 [{week_start}]，内容长度: {len(content)}")
        return digest

    if session is not None:
        return await _run(session)
    else:
        async with async_session() as sess:
            result = await _run(sess)
            await sess.commit()
            return result


async def _call_llm_for_digest(prompt: str) -> str:
    """调用 LLM 生成摘要内容"""
    from langchain_openai import ChatOpenAI
    from app.config import settings

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        max_tokens=2000,
    )

    response = await llm.ainvoke(prompt)
    return response.content


def _format_trends_for_prompt(trends: list[dict]) -> str:
    """格式化趋势数据为 LLM 可读文本"""
    if not trends:
        return "本周暂无显著趋势话题。"

    lines = []
    for i, t in enumerate(trends, 1):
        name = t.get("tag_name", "未知")
        current = t.get("current_count", 0)
        prev = t.get("previous_count", 0)
        growth = t.get("growth_rate", 0)
        is_new = t.get("is_new_topic", False)

        if is_new:
            lines.append(f"{i}. 🆕 {name} — 本周新增 {current} 篇（新话题）")
        else:
            lines.append(
                f"{i}. {name} — 本周 {current} 篇, 上周 {prev} 篇, "
                f"增长 {growth * 100:.1f}%"
            )
    return "\n".join(lines)


def _format_distribution_for_prompt(distribution: list[dict]) -> str:
    """格式化分类分布为 LLM 可读文本"""
    if not distribution:
        return "暂无分类分布数据。"

    lines = []
    for d in distribution:
        name_zh = d.get("category_name_zh") or d.get("category_name", "未知")
        count = d.get("count", 0)
        pct = d.get("percentage", 0)
        lines.append(f"- {name_zh}: {count} 篇 ({pct}%)")
    return "\n".join(lines)


def _generate_fallback_digest(
    trends: list[dict],
    distribution: list[dict],
    week_start: date,
) -> str:
    """LLM 不可用时的降级摘要"""
    week_end = week_start + timedelta(days=6)
    lines = [
        f"# 每周趋势摘要 ({week_start} ~ {week_end})",
        "",
        "## 热门趋势",
    ]

    if trends:
        for t in trends[:5]:
            name = t.get("tag_name", "未知")
            current = t.get("current_count", 0)
            growth = t.get("growth_rate", 0)
            lines.append(f"- **{name}**: {current} 篇文章, 增长 {growth * 100:.1f}%")
    else:
        lines.append("- 本周暂无显著趋势")

    lines.extend(["", "## 分类分布"])

    if distribution:
        for d in distribution:
            name_zh = d.get("category_name_zh") or d.get("category_name", "未知")
            count = d.get("count", 0)
            pct = d.get("percentage", 0)
            lines.append(f"- {name_zh}: {count} 篇 ({pct}%)")
    else:
        lines.append("- 暂无分类数据")

    return "\n".join(lines)


async def run_weekly_digest_job() -> None:
    """供调度器调用的每周摘要生成入口"""
    try:
        digest = await generate_weekly_digest()
        if digest:
            logger.info(f"每周摘要调度任务完成: {digest.week_start}")
        else:
            logger.info("每周摘要调度任务: 本周摘要已存在，无需生成")
    except Exception as e:
        logger.error(f"每周摘要调度任务失败: {e}")
