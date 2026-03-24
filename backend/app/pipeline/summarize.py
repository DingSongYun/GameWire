"""AI 摘要生成模块：LangChain + OpenAI GPT-4o-mini"""
import logging
from datetime import date, timezone, datetime

import redis.asyncio as aioredis
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Redis key 前缀
TOKEN_BUDGET_KEY_PREFIX = "gamewire:token_budget:"


def _get_llm() -> ChatOpenAI:
    """获取 LLM 实例"""
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
        max_tokens=500,
    )


async def _get_daily_token_usage(redis_client: aioredis.Redis) -> int:
    """获取今日已使用的 token 数量"""
    key = f"{TOKEN_BUDGET_KEY_PREFIX}{date.today().isoformat()}"
    usage = await redis_client.get(key)
    return int(usage) if usage else 0


async def _increment_token_usage(redis_client: aioredis.Redis, tokens: int) -> None:
    """增加今日 token 使用量"""
    key = f"{TOKEN_BUDGET_KEY_PREFIX}{date.today().isoformat()}"
    await redis_client.incrby(key, tokens)
    # 设置 key 过期时间为 48 小时
    await redis_client.expire(key, 172800)


async def check_budget(redis_client: aioredis.Redis) -> bool:
    """检查今日 token 预算是否耗尽"""
    usage = await _get_daily_token_usage(redis_client)
    return usage < settings.llm_daily_token_budget


async def generate_summary(
    content: str,
    title: str,
    redis_client: aioredis.Redis | None = None,
) -> tuple[str, int]:
    """
    为文章生成 AI 摘要。

    Args:
        content: 清洗后的文章内容
        title: 文章标题
        redis_client: Redis 客户端（用于 token 预算追踪）

    Returns:
        tuple[str, int]: (摘要文本, 使用的 token 数)
    """
    # 预算检查
    if redis_client and not await check_budget(redis_client):
        logger.warning("每日 LLM token 预算已耗尽，使用截断摘录")
        return _fallback_excerpt(content), 0

    if not settings.openai_api_key:
        logger.warning("OpenAI API Key 未配置，使用截断摘录")
        return _fallback_excerpt(content), 0

    try:
        llm = _get_llm()

        # 截断过长的内容（避免 token 超限）
        truncated = content[:3000] if len(content) > 3000 else content

        messages = [
            SystemMessage(content=(
                "你是一个游戏行业技术资讯编辑。请为以下文章生成一个简洁的中文摘要（100-200字），"
                "重点关注对游戏行业技术决策者有价值的信息。"
                "直接输出摘要内容，不要加标题或前缀。"
            )),
            HumanMessage(content=f"标题: {title}\n\n内容:\n{truncated}"),
        ]

        response = await llm.ainvoke(messages)
        summary = response.content.strip()
        tokens_used = response.response_metadata.get("token_usage", {}).get("total_tokens", 0)

        # 更新 token 使用量
        if redis_client and tokens_used > 0:
            await _increment_token_usage(redis_client, tokens_used)

        logger.debug(f"AI 摘要生成成功: {len(summary)} 字, {tokens_used} tokens")
        return summary, tokens_used

    except Exception as e:
        logger.error(f"AI 摘要生成失败: {e}")
        return _fallback_excerpt(content), 0


def _fallback_excerpt(content: str) -> str:
    """回退方案：截取前 200 个字符作为临时摘要"""
    if not content:
        return ""
    excerpt = content[:200].strip()
    if len(content) > 200:
        excerpt += "..."
    return excerpt
