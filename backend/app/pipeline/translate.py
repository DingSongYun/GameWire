"""AI 翻译模块：中英文摘要互译"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        max_tokens=500,
    )


async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    使用 LLM 翻译文本。

    Args:
        text: 要翻译的文本
        source_lang: 源语言代码 (zh/en)
        target_lang: 目标语言代码 (zh/en)

    Returns:
        str: 翻译后的文本
    """
    if not settings.openai_api_key:
        logger.warning("OpenAI API Key 未配置，跳过翻译")
        return ""

    if source_lang == target_lang:
        return text

    lang_map = {"zh": "中文", "en": "English"}
    src = lang_map.get(source_lang, source_lang)
    tgt = lang_map.get(target_lang, target_lang)

    try:
        llm = _get_llm()
        messages = [
            SystemMessage(content=(
                f"请将以下{src}文本翻译为{tgt}。"
                "保持专业术语的准确性，直接输出翻译结果，不要加任何额外说明。"
            )),
            HumanMessage(content=text),
        ]

        response = await llm.ainvoke(messages)
        translated = response.content.strip()
        logger.debug(f"翻译完成: {source_lang} → {target_lang}, {len(translated)} 字")
        return translated

    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return ""


async def translate_summary_to_zh(summary: str) -> str:
    """将英文摘要翻译为中文"""
    return await translate_text(summary, "en", "zh")


async def translate_summary_to_en(summary: str) -> str:
    """将中文摘要翻译为英文"""
    return await translate_text(summary, "zh", "en")
