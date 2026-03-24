"""GitHub Trending 适配器"""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.config import settings
from app.models.models import SourceType

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

DEFAULT_TOPICS = [
    "gamedev", "game-engine", "game-development",
    "machine-learning", "artificial-intelligence", "deep-learning",
    "reinforcement-learning", "procedural-generation",
]


@register_adapter
class GitHubAdapter(SourceAdapter):
    """GitHub REST API 热门仓库适配器"""

    source_type = SourceType.GITHUB

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.topics: list[str] = config.get("topics", DEFAULT_TOPICS)
        self.token: str = config.get("token", settings.github_token)
        self.per_topic_limit: int = config.get("per_topic_limit", 5)

    async def fetch(self) -> list[RawArticle]:
        """抓取 GitHub 上按主题筛选的热门仓库"""
        articles = []
        seen_urls = set()

        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            for topic in self.topics:
                try:
                    response = await client.get(
                        f"{GITHUB_API_BASE}/search/repositories",
                        headers=headers,
                        params={
                            "q": f"topic:{topic}",
                            "sort": "stars",
                            "order": "desc",
                            "per_page": self.per_topic_limit,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    for repo in data.get("items", []):
                        url = repo.get("html_url", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)

                        pushed_at = None
                        if repo.get("pushed_at"):
                            pushed_at = datetime.fromisoformat(
                                repo["pushed_at"].replace("Z", "+00:00")
                            )

                        articles.append(
                            RawArticle(
                                title=f"{repo.get('full_name', '')} — {repo.get('description', '')}",
                                url=url,
                                content_snippet=repo.get("description"),
                                author=repo.get("owner", {}).get("login"),
                                published_at=pushed_at,
                                source_name="GitHub",
                                raw_metadata={
                                    "stars": repo.get("stargazers_count", 0),
                                    "forks": repo.get("forks_count", 0),
                                    "language": repo.get("language"),
                                    "topics": repo.get("topics", []),
                                    "open_issues": repo.get("open_issues_count", 0),
                                },
                            )
                        )

                except httpx.HTTPStatusError as e:
                    logger.error(f"GitHub topic '{topic}' 搜索失败: {e.response.status_code}")

        logger.info(f"GitHub 抓取到 {len(articles)} 个仓库")
        return articles

    async def health_check(self) -> bool:
        """检查 GitHub API 是否可用"""
        try:
            headers = {"Accept": "application/vnd.github+json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{GITHUB_API_BASE}/rate_limit", headers=headers)
                return response.status_code == 200
        except Exception:
            return False
