"""内容去重模块：URL 精确匹配 + SimHash 内容相似度检测"""
import hashlib
import logging
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article

logger = logging.getLogger(__name__)

# SimHash 汉明距离阈值（默认 3 位）
DEFAULT_HAMMING_THRESHOLD = 3


async def is_url_duplicate(url: str, session: AsyncSession) -> bool:
    """检查 URL 是否已存在于数据库"""
    result = await session.execute(select(Article.id).where(Article.url == url))
    return result.scalar_one_or_none() is not None


# ==================== SimHash 实现 ====================


def _tokenize(text: str) -> list[str]:
    """将文本分词为 token 列表"""
    # 简单的基于空格和标点的分词
    text = text.lower()
    tokens = re.findall(r"\w{2,}", text)
    # 生成 bigram 增强相似度检测
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return tokens + bigrams


def _hash_token(token: str) -> int:
    """将 token 哈希为 64 位整数"""
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def compute_simhash(text: str) -> str:
    """
    计算文本的 SimHash 指纹。

    Returns:
        str: 16 位十六进制字符串表示的 64 位指纹
    """
    if not text:
        return "0" * 16

    tokens = _tokenize(text)
    if not tokens:
        return "0" * 16

    # 初始化 64 维向量
    v = [0] * 64

    for token in tokens:
        h = _hash_token(token)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    # 生成指纹
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return f"{fingerprint:016x}"


def hamming_distance(hash1: str, hash2: str) -> int:
    """计算两个 SimHash 指纹的汉明距离"""
    val1 = int(hash1, 16)
    val2 = int(hash2, 16)
    xor = val1 ^ val2
    return bin(xor).count("1")


async def find_similar_article(
    simhash: str,
    session: AsyncSession,
    threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> Optional[Article]:
    """
    在数据库中查找与给定 SimHash 相似的文章。

    Returns:
        Optional[Article]: 如果找到相似文章则返回，否则返回 None
    """
    if simhash == "0" * 16:
        return None

    # 获取所有有指纹的文章（生产环境应使用更高效的检索方式）
    result = await session.execute(
        select(Article).where(Article.simhash_fingerprint.isnot(None)).limit(5000)
    )
    articles = result.scalars().all()

    for article in articles:
        if article.simhash_fingerprint and hamming_distance(simhash, article.simhash_fingerprint) <= threshold:
            return article

    return None


async def check_duplicate(
    url: str,
    content: str,
    session: AsyncSession,
    threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> tuple[bool, Optional[str], Optional[Article]]:
    """
    综合去重检查（URL + SimHash）。

    Returns:
        tuple[bool, Optional[str], Optional[Article]]:
            (是否重复, SimHash 指纹, 原始文章（如果是相似重复）)
    """
    # 1. URL 精确去重
    if await is_url_duplicate(url, session):
        logger.debug(f"URL 去重: {url}")
        return True, None, None

    # 2. SimHash 内容去重
    simhash = compute_simhash(content)
    similar = await find_similar_article(simhash, session, threshold)
    if similar:
        logger.debug(f"SimHash 去重: {url} 与 {similar.url} 相似")
        return True, simhash, similar

    return False, simhash, None
