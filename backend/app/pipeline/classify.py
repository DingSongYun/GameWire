"""AI 分类与标签提取模块"""
import json
import logging
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import ArticleCategory, ArticleTag, Category, Tag

logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        max_tokens=500,
    )


async def classify_and_tag(
    title: str,
    content: str,
    article_id: uuid.UUID,
    session: AsyncSession,
    confidence_threshold: float = 0.5,
) -> tuple[list[dict], list[str]]:
    """
    对文章进行 AI 分类并提取标签。

    Returns:
        tuple[list[dict], list[str]]: (分类列表 [{name, confidence}], 标签列表)
    """
    if not settings.openai_api_key:
        logger.warning("OpenAI API Key 未配置，跳过分类和标签提取")
        return [], []

    # 获取当前活跃的分类列表
    result = await session.execute(
        select(Category).where(Category.is_active == True)  # noqa: E712
    )
    categories = result.scalars().all()
    category_names = [f"{c.name_zh or c.name} ({c.name})" for c in categories]

    try:
        llm = _get_llm()
        truncated = content[:2000] if len(content) > 2000 else content

        messages = [
            SystemMessage(content=(
                "你是一个游戏行业资讯分类专家。请分析以下文章，完成两个任务：\n\n"
                "1. 从以下分类中选择适用的类别，并给出置信度分数(0.0-1.0):\n"
                f"   可选分类: {', '.join(category_names)}\n\n"
                "2. 提取 3-8 个关键标签（技术名词、公司名、产品名、概念等）\n\n"
                "请严格以 JSON 格式输出:\n"
                '{"categories": [{"name": "英文分类名", "confidence": 0.9}], '
                '"tags": ["标签1", "标签2"]}'
            )),
            HumanMessage(content=f"标题: {title}\n\n内容:\n{truncated}"),
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content.strip()

        # 解析 JSON（处理可能的 markdown 代码块包裹）
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        parsed = json.loads(response_text)
        ai_categories = parsed.get("categories", [])
        ai_tags = parsed.get("tags", [])

        # 存储分类关联
        saved_categories = []
        for cat_item in ai_categories:
            confidence = cat_item.get("confidence", 0)
            if confidence < confidence_threshold:
                continue

            cat_name = cat_item.get("name", "")
            # 查找匹配的分类
            matched_cat = None
            for c in categories:
                if c.name.lower() == cat_name.lower() or c.name_zh == cat_name:
                    matched_cat = c
                    break

            if matched_cat:
                ac = ArticleCategory(
                    article_id=article_id,
                    category_id=matched_cat.id,
                    confidence_score=confidence,
                )
                session.add(ac)
                saved_categories.append({"name": matched_cat.name, "confidence": confidence})

        # 存储标签
        saved_tags = []
        for tag_name in ai_tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue

            tag = await _normalize_tag(tag_name, session)
            # 创建文章-标签关联
            existing = await session.execute(
                select(ArticleTag).where(
                    ArticleTag.article_id == article_id,
                    ArticleTag.tag_id == tag.id,
                )
            )
            if existing.scalar_one_or_none() is None:
                at = ArticleTag(article_id=article_id, tag_id=tag.id)
                session.add(at)
            saved_tags.append(tag.canonical_name)

        logger.debug(f"分类: {saved_categories}, 标签: {saved_tags}")
        return saved_categories, saved_tags

    except Exception as e:
        logger.error(f"AI 分类/标签提取失败: {e}")
        return [], []


async def _normalize_tag(tag_name: str, session: AsyncSession) -> Tag:
    """
    标签归一化：查找已有的规范标签或创建新标签。
    检查 canonical_name 和 aliases 中是否存在匹配。
    """
    tag_lower = tag_name.lower().strip()

    # 精确匹配 canonical_name
    result = await session.execute(
        select(Tag).where(Tag.canonical_name.ilike(tag_lower))
    )
    tag = result.scalar_one_or_none()
    if tag:
        return tag

    # 搜索别名（JSONB 数组包含检查）
    all_tags_result = await session.execute(select(Tag))
    for existing_tag in all_tags_result.scalars().all():
        if existing_tag.aliases:
            aliases_lower = [a.lower() for a in existing_tag.aliases]
            if tag_lower in aliases_lower:
                return existing_tag

    # 未找到匹配，创建新标签
    new_tag = Tag(
        id=uuid.uuid4(),
        canonical_name=tag_name.strip(),
        aliases=[],
    )
    session.add(new_tag)
    await session.flush()
    logger.debug(f"创建新标签: {tag_name}")
    return new_tag
