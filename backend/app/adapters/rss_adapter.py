"""RSS/Atom 订阅源适配器"""
import logging
from datetime import datetime, timezone
from time import mktime
from typing import Any

import feedparser
import httpx

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.models.models import SourceType

logger = logging.getLogger(__name__)


@register_adapter
class RSSAdapter(SourceAdapter):
    """RSS 2.0 / Atom 订阅源适配器"""

    source_type = SourceType.RSS

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.feed_url: str = config["feed_url"]
        self.name: str = config.get("name", "RSS Feed")

    async def fetch(self) -> list[RawArticle]:
        """抓取并解析 RSS/Atom 订阅源"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.feed_url, follow_redirects=True)
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        articles = []

        for entry in feed.entries:
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_at = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)

            articles.append(
                RawArticle(
                    title=entry.get("title", "无标题"),
                    url=entry.get("link", ""),
                    content_snippet=entry.get("summary") or entry.get("description", ""),
                    author=entry.get("author"),
                    published_at=published_at,
                    source_name=self.name,
                    raw_metadata={
                        "feed_url": self.feed_url,
                        "feed_title": feed.feed.get("title", ""),
                        "tags": [tag.term for tag in entry.get("tags", [])],
                    },
                )
            )

        logger.info(f"RSS [{self.name}] 抓取到 {len(articles)} 篇文章")
        return articles

    async def health_check(self) -> bool:
        """检查 RSS 订阅源是否可达"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(self.feed_url, follow_redirects=True)
                return response.status_code < 400
        except Exception:
            return False
