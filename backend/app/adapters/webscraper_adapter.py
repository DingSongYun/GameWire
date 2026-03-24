"""通用网页爬虫适配器"""
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.adapters.base import RawArticle, SourceAdapter
from app.adapters.registry import register_adapter
from app.models.models import SourceType

logger = logging.getLogger(__name__)


@register_adapter
class WebScraperAdapter(SourceAdapter):
    """通用网页爬虫适配器，支持每个网站可配置的 CSS 选择器"""

    source_type = SourceType.WEBSCRAPER

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.base_url: str = config["base_url"]
        self.list_url: str = config.get("list_url", self.base_url)
        self.name: str = config.get("name", urlparse(self.base_url).hostname or "Website")
        # CSS 选择器配置
        self.selectors = config.get("selectors", {})
        self.article_selector: str = self.selectors.get("article", "article")
        self.title_selector: str = self.selectors.get("title", "h2 a, h3 a, .title a")
        self.summary_selector: str = self.selectors.get("summary", "p, .summary, .excerpt")
        self.author_selector: str = self.selectors.get("author", ".author, .byline")
        self.date_selector: str = self.selectors.get("date", "time, .date, .published")

    async def _check_robots_txt(self, client: httpx.AsyncClient) -> set[str]:
        """获取 robots.txt 中禁止的路径"""
        disallowed = set()
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            response = await client.get(robots_url, timeout=10.0)
            if response.status_code == 200:
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            disallowed.add(path)
        except Exception:
            pass
        return disallowed

    def _is_path_allowed(self, url: str, disallowed_paths: set[str]) -> bool:
        """检查 URL 路径是否被 robots.txt 允许"""
        parsed = urlparse(url)
        for path in disallowed_paths:
            if parsed.path.startswith(path):
                return False
        return True

    async def fetch(self) -> list[RawArticle]:
        """爬取配置的资讯网站"""
        articles = []
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "GameWire/0.1.0 (News Aggregator)"},
            follow_redirects=True,
        ) as client:
            # 检查 robots.txt
            disallowed = await self._check_robots_txt(client)

            if not self._is_path_allowed(self.list_url, disallowed):
                logger.warning(f"[{self.name}] 列表页 URL 被 robots.txt 禁止")
                return []

            # 抓取列表页
            response = await client.get(self.list_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            article_elements = soup.select(self.article_selector)

            for element in article_elements[:30]:  # 限制最多 30 条
                try:
                    # 提取标题和链接
                    title_el = element.select_one(self.title_selector)
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    link = title_el.get("href", "")
                    if link and not link.startswith("http"):
                        link = urljoin(self.base_url, link)

                    if not title or not link:
                        continue

                    # 检查链接是否被允许
                    if not self._is_path_allowed(link, disallowed):
                        continue

                    # 提取摘要
                    summary_el = element.select_one(self.summary_selector)
                    summary = summary_el.get_text(strip=True) if summary_el else None

                    # 提取作者
                    author_el = element.select_one(self.author_selector)
                    author = author_el.get_text(strip=True) if author_el else None

                    articles.append(
                        RawArticle(
                            title=title,
                            url=link,
                            content_snippet=summary,
                            author=author,
                            published_at=None,
                            source_name=self.name,
                            raw_metadata={"base_url": self.base_url},
                        )
                    )

                except Exception as e:
                    logger.debug(f"[{self.name}] 解析文章元素失败: {e}")

        logger.info(f"WebScraper [{self.name}] 抓取到 {len(articles)} 篇文章")
        return articles

    async def health_check(self) -> bool:
        """检查目标网站是否可达"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.head(self.base_url)
                return response.status_code < 400
        except Exception:
            return False
