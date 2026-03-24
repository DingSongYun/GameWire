"""Reddit API 适配器"""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.config import settings
from app.models.models import SourceType

logger = logging.getLogger(__name__)

REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"


@register_adapter
class RedditAdapter(SourceAdapter):
    """Reddit OAuth2 API 适配器"""

    source_type = SourceType.REDDIT

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.subreddits: list[str] = config.get("subreddits", ["gamedev"])
        self.sort: str = config.get("sort", "hot")  # hot, new, top
        self.limit: int = config.get("limit", 25)
        self.client_id: str = config.get("client_id", settings.reddit_client_id)
        self.client_secret: str = config.get("client_secret", settings.reddit_client_secret)
        self.user_agent: str = config.get("user_agent", settings.reddit_user_agent)
        self._access_token: str | None = None

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        """获取 Reddit OAuth2 访问令牌"""
        if self._access_token:
            return self._access_token

        response = await client.post(
            REDDIT_TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.user_agent},
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        return self._access_token

    async def fetch(self) -> list[RawArticle]:
        """从配置的子版块抓取帖子"""
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API 凭证未配置，跳过采集")
            return []

        articles = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = await self._get_access_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent,
            }

            for subreddit in self.subreddits:
                try:
                    url = f"{REDDIT_API_BASE}/r/{subreddit}/{self.sort}"
                    response = await client.get(
                        url, headers=headers, params={"limit": self.limit}
                    )
                    response.raise_for_status()
                    data = response.json()

                    for post in data.get("data", {}).get("children", []):
                        post_data = post["data"]
                        published_at = datetime.fromtimestamp(
                            post_data.get("created_utc", 0), tz=timezone.utc
                        )

                        content = post_data.get("selftext", "") or post_data.get("url", "")

                        articles.append(
                            RawArticle(
                                title=post_data.get("title", ""),
                                url=f"https://reddit.com{post_data.get('permalink', '')}",
                                content_snippet=content[:500] if content else None,
                                author=post_data.get("author"),
                                published_at=published_at,
                                source_name=f"r/{subreddit}",
                                raw_metadata={
                                    "subreddit": subreddit,
                                    "score": post_data.get("score", 0),
                                    "num_comments": post_data.get("num_comments", 0),
                                    "upvote_ratio": post_data.get("upvote_ratio", 0),
                                    "link_url": post_data.get("url"),
                                },
                            )
                        )

                except httpx.HTTPStatusError as e:
                    logger.error(f"Reddit r/{subreddit} 抓取失败: {e.response.status_code}")

        logger.info(f"Reddit 抓取到 {len(articles)} 个帖子")
        return articles

    async def health_check(self) -> bool:
        """检查 Reddit API 是否可用"""
        if not self.client_id or not self.client_secret:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await self._get_access_token(client)
                return True
        except Exception:
            return False
