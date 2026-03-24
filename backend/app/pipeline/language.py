"""语言检测模块"""
import logging

from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """
    检测文本语言。

    Returns:
        str: 语言代码 (zh/en/unknown)
    """
    if not text or len(text.strip()) < 10:
        return "unknown"

    try:
        lang = detect(text)
        # 归一化语言代码
        if lang.startswith("zh"):
            return "zh"
        elif lang == "en":
            return "en"
        else:
            return lang
    except LangDetectException:
        logger.debug("语言检测失败")
        return "unknown"
