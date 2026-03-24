"""Hacker News Firebase API 适配器"""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.models.models import SourceType

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# 默认关键词过滤列表
DEFAULT_KEYWORDS = [
    "game", "gaming", "gamedev", "game engine", "unity", "unreal",
    "godot", "AI", "machine learning", "neural", "LLM", "GPT",
    "deep learning", "reinforcement learning", "procedural generation",
    "游戏", "人工智能",
]


@register_adapter
class HackerNewsAdapter(SourceAdapter):
    """Hacker News Firebase API 适配器"""

    source_type = SourceType.HACKERNEWS

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.max_stories: int = config.get("max_stories", 50)
        self.keywords: list[str] = config.get("keywords", DEFAULT_KEYWORDS)

    def _is_relevant(self, title: str) -> bool:
        """检查标题是否与配置的关键词相关"""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in self.keywords)

    async def fetch(self) -> list[RawArticle]:
        """抓取 HN 热门文章并按关键词过滤"""
        articles = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 获取热门文章 ID
            response = await client.get(f"{HN_API_BASE}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()[:self.max_stories]

            # 逐个获取文章详情
            for story_id in story_ids:
                try:
                    resp = await client.get(f"{HN_API_BASE}/item/{story_id}.json")
                    resp.raise_for_status()
                    item = resp.json()

                    if not item or item.get("type") != "story":
                        continue

                    title = item.get("title", "")
                    if not self._is_relevant(title):
                        continue

                    published_at = None
                    if "time" in item:
                        published_at = datetime.fromtimestamp(item["time"], tz=timezone.utc)

                    url = item.get("url", f"https://news.ycombinator.com/item?id={story_id}")

                    articles.append(
                        RawArticle(
                            title=title,
                            url=url,
                            content_snippet=item.get("text"),
                            author=item.get("by"),
                            published_at=published_at,
                            source_name="Hacker News",
                            raw_metadata={
                                "hn_id": story_id,
                                "score": item.get("score", 0),
                                "descendants": item.get("descendants", 0),
                            },
                        )
                    )

                except Exception as e:
                    logger.debug(f"HN story {story_id} 获取失败: {e}")

        logger.info(f"Hacker News 抓取到 {len(articles)} 篇相关文章")
        return articles

    async def health_check(self) -> bool:
        """检查 HN API 是否可用"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{HN_API_BASE}/topstories.json")
                return response.status_code == 200
        except Exception:
            return False
