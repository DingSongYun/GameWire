"""Twitter/X API v2 适配器"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.config import settings
from app.models.models import SourceType

logger = logging.getLogger(__name__)

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


@register_adapter
class TwitterAdapter(SourceAdapter):
    """Twitter/X API v2 关键词搜索适配器"""

    source_type = SourceType.TWITTER

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.keywords: list[str] = config.get("keywords", [])
        self.bearer_token: str = config.get("bearer_token", settings.twitter_bearer_token)
        self.max_results: int = config.get("max_results", 20)

    async def fetch(self) -> list[RawArticle]:
        """通过 Twitter API v2 关键词搜索抓取推文"""
        if not self.bearer_token:
            logger.warning("Twitter bearer token 未配置，跳过采集")
            return []

        query = " OR ".join(f'"{kw}"' for kw in self.keywords)
        if not query:
            return []

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "query": f"{query} -is:retweet lang:en OR lang:zh",
            "max_results": min(self.max_results, 100),
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "expansions": "author_id",
            "user.fields": "username,name",
        }

        articles = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(TWITTER_SEARCH_URL, headers=headers, params=params)

                # 速率限制处理
                if response.status_code == 429:
                    reset_time = int(response.headers.get("x-rate-limit-reset", 0))
                    wait_seconds = max(reset_time - int(datetime.now(timezone.utc).timestamp()), 60)
                    logger.warning(f"Twitter API 速率限制，等待 {wait_seconds} 秒")
                    await asyncio.sleep(min(wait_seconds, 300))  # 最多等 5 分钟
                    response = await client.get(TWITTER_SEARCH_URL, headers=headers, params=params)

                response.raise_for_status()
                data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Twitter API 错误: {e.response.status_code}")
                raise

        # 构建用户名映射
        users = {}
        for user in data.get("includes", {}).get("users", []):
            users[user["id"]] = user.get("name", user.get("username", ""))

        for tweet in data.get("data", []):
            published_at = None
            if "created_at" in tweet:
                published_at = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))

            articles.append(
                RawArticle(
                    title=tweet["text"][:120],
                    url=f"https://twitter.com/i/web/status/{tweet['id']}",
                    content_snippet=tweet["text"],
                    author=users.get(tweet.get("author_id"), ""),
                    published_at=published_at,
                    source_name="Twitter/X",
                    raw_metadata={
                        "tweet_id": tweet["id"],
                        "metrics": tweet.get("public_metrics", {}),
                        "lang": tweet.get("lang"),
                    },
                )
            )

        logger.info(f"Twitter 抓取到 {len(articles)} 条推文")
        return articles

    async def health_check(self) -> bool:
        """检查 Twitter API 是否可用"""
        if not self.bearer_token:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    TWITTER_SEARCH_URL,
                    headers=headers,
                    params={"query": "test", "max_results": 10},
                )
                return response.status_code != 401
        except Exception:
            return False
