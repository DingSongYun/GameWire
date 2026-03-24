"""适配器单元测试 — 验证各 SourceAdapter 输出符合 RawArticle Schema"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.adapters.base import RawArticle


# ─── RSS Adapter ───

@pytest.mark.asyncio
async def test_rss_adapter_fetch():
    from app.adapters.rss_adapter import RSSAdapter

    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="Test RSS Article",
            link="https://example.com/article-1",
            get=lambda k, d=None: {
                "summary": "Test summary content",
                "author": "Test Author",
            }.get(k, d),
            published_parsed=(2024, 1, 15, 10, 0, 0, 0, 0, 0),
        )
    ]

    with patch("app.adapters.rss_adapter.feedparser.parse", return_value=mock_feed):
        adapter = RSSAdapter({"feed_url": "https://example.com/feed.xml"})
        articles = await adapter.fetch()

    assert len(articles) >= 1
    article = articles[0]
    assert isinstance(article, RawArticle)
    assert article.title == "Test RSS Article"
    assert article.url == "https://example.com/article-1"


# ─── HackerNews Adapter ───

@pytest.mark.asyncio
async def test_hackernews_adapter_fetch():
    from app.adapters.hackernews_adapter import HackerNewsAdapter

    mock_response_ids = AsyncMock()
    mock_response_ids.json = AsyncMock(return_value=[1001, 1002])
    mock_response_ids.raise_for_status = MagicMock()

    mock_response_item = AsyncMock()
    mock_response_item.json = AsyncMock(return_value={
        "id": 1001,
        "title": "AI in Game Development",
        "url": "https://example.com/ai-games",
        "by": "hacker",
        "time": 1705300000,
        "score": 100,
    })
    mock_response_item.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_response_ids, mock_response_item, mock_response_item])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.adapters.hackernews_adapter.httpx.AsyncClient", return_value=mock_client):
        adapter = HackerNewsAdapter({"keywords": ["AI", "game"], "limit": 2})
        articles = await adapter.fetch()

    assert len(articles) >= 1
    for a in articles:
        assert isinstance(a, RawArticle)
        assert a.url is not None


# ─── GitHub Adapter ───

@pytest.mark.asyncio
async def test_github_adapter_fetch():
    from app.adapters.github_adapter import GitHubAdapter

    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "items": [
            {
                "full_name": "user/game-engine",
                "html_url": "https://github.com/user/game-engine",
                "description": "A cool game engine with AI features",
                "owner": {"login": "user"},
                "created_at": "2024-01-10T00:00:00Z",
                "stargazers_count": 500,
                "language": "C++",
                "topics": ["game", "ai"],
            }
        ]
    })
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.adapters.github_adapter.httpx.AsyncClient", return_value=mock_client):
        adapter = GitHubAdapter({"topics": ["game-engine"], "min_stars": 100})
        articles = await adapter.fetch()

    assert len(articles) == 1
    assert isinstance(articles[0], RawArticle)
    assert "game-engine" in articles[0].url


# ─── Reddit Adapter ───

@pytest.mark.asyncio
async def test_reddit_adapter_fetch():
    from app.adapters.reddit_adapter import RedditAdapter

    # Mock OAuth token
    mock_token_resp = AsyncMock()
    mock_token_resp.json = AsyncMock(return_value={"access_token": "test_token"})
    mock_token_resp.raise_for_status = MagicMock()

    # Mock subreddit listing
    mock_listing_resp = AsyncMock()
    mock_listing_resp.json = AsyncMock(return_value={
        "data": {
            "children": [
                {
                    "data": {
                        "title": "New AI technique in gaming",
                        "url": "https://reddit.com/r/gamedev/test",
                        "permalink": "/r/gamedev/comments/test",
                        "selftext": "Some text about AI in games",
                        "author": "redditor",
                        "created_utc": 1705300000,
                        "score": 50,
                    }
                }
            ]
        }
    })
    mock_listing_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_token_resp)
    mock_client.get = AsyncMock(return_value=mock_listing_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.adapters.reddit_adapter.httpx.AsyncClient", return_value=mock_client):
        adapter = RedditAdapter({
            "subreddits": ["gamedev"],
            "client_id": "test",
            "client_secret": "test",
        })
        articles = await adapter.fetch()

    assert len(articles) >= 1
    assert isinstance(articles[0], RawArticle)
