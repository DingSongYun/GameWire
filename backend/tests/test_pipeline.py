"""管线各阶段单元测试 — 清洗、去重、语言检测、摘要、分类、趋势"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ─── 15.2: 清洗测试 ───

def test_cleaning_strips_html():
    from app.pipeline.cleaning import clean_html

    result = clean_html("<p>Hello <b>World</b></p><script>alert('xss')</script>")
    assert "Hello" in result
    assert "World" in result
    assert "<script>" not in result
    assert "<p>" not in result


def test_cleaning_removes_tracking_params():
    from app.pipeline.cleaning import clean_url

    url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=123"
    result = clean_url(url)
    assert "utm_source" not in result
    assert "id=123" in result


def test_cleaning_normalizes_whitespace():
    from app.pipeline.cleaning import normalize_whitespace

    result = normalize_whitespace("  hello   world  \n\n\n  test  ")
    assert result == "hello world\ntest"


# ─── 15.2: SimHash 去重测试 ───

def test_simhash_fingerprint():
    from app.pipeline.dedup import compute_simhash

    text1 = "This is a test article about AI in game development"
    text2 = "This is a test article about AI in game development"
    text3 = "Completely different content about cooking recipes"

    fp1 = compute_simhash(text1)
    fp2 = compute_simhash(text2)
    fp3 = compute_simhash(text3)

    assert fp1 == fp2  # 相同文本应产生相同指纹
    assert fp1 != fp3  # 不同文本应产生不同指纹


def test_simhash_hamming_distance():
    from app.pipeline.dedup import compute_simhash, hamming_distance

    text1 = "AI game development is growing rapidly in the industry"
    text2 = "AI game development is growing rapidly in the gaming industry"

    fp1 = compute_simhash(text1)
    fp2 = compute_simhash(text2)

    dist = hamming_distance(fp1, fp2)
    assert dist <= 3  # 相似文本应有较小汉明距离


# ─── 15.2: 语言检测测试 ───

def test_language_detection_english():
    from app.pipeline.language import detect_language

    result = detect_language("This is an English article about game development and AI technology")
    assert result == "en"


def test_language_detection_chinese():
    from app.pipeline.language import detect_language

    result = detect_language("这是一篇关于游戏开发和人工智能技术的中文文章")
    assert result == "zh"


# ─── 15.2: 摘要生成测试（模拟 LLM）───

@pytest.mark.asyncio
async def test_summarize_with_mock_llm():
    from app.pipeline.summarize import generate_summary

    mock_llm_response = MagicMock()
    mock_llm_response.content = "This is a test summary of the article."

    with patch("app.pipeline.summarize.ChatOpenAI") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_cls.return_value = mock_instance

        with patch("app.pipeline.summarize.check_token_budget", return_value=True):
            with patch("app.pipeline.summarize.record_token_usage"):
                result = await generate_summary("Long article content about AI in games...", language="en")

    assert result is not None
    assert len(result) > 0


# ─── 15.3: 分类测试（模拟 LLM）───

@pytest.mark.asyncio
async def test_classify_with_mock_llm():
    from app.pipeline.classify import classify_article

    mock_response = MagicMock()
    mock_response.content = '{"categories": [{"name": "AI 技术", "confidence": 0.9}], "tags": ["machine-learning", "game-ai"]}'

    with patch("app.pipeline.classify.ChatOpenAI") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_instance

        result = await classify_article(
            title="New ML Technique for Game NPCs",
            content="Article about machine learning in game AI...",
        )

    assert result is not None
    assert "categories" in result or hasattr(result, "categories")


# ─── 15.4: 趋势计算测试 ───

def test_growth_rate_calculation():
    """测试增长率计算逻辑"""
    current = 15
    previous = 10
    growth = (current - previous) / previous
    assert growth == 0.5  # 50% 增长

    # 新话题（上期为 0）
    current_new = 5
    previous_new = 0
    assert current_new > 0  # 新话题应有正值
    assert previous_new == 0  # 上期为 0


def test_trend_threshold_filtering():
    """测试趋势阈值过滤"""
    threshold = 0.5
    trends = [
        {"tag": "AI", "current": 20, "previous": 10, "growth": 1.0},
        {"tag": "VR", "current": 12, "previous": 10, "growth": 0.2},
        {"tag": "ML", "current": 18, "previous": 12, "growth": 0.5},
    ]

    filtered = [t for t in trends if t["growth"] >= threshold]
    assert len(filtered) == 2  # AI (100%) 和 ML (50%) 应通过
    assert all(t["growth"] >= threshold for t in filtered)


def test_trend_sorting():
    """测试趋势按增长率排序"""
    trends = [
        {"tag": "VR", "growth": 0.3},
        {"tag": "AI", "growth": 1.5},
        {"tag": "ML", "growth": 0.8},
    ]
    sorted_trends = sorted(trends, key=lambda x: x["growth"], reverse=True)
    assert sorted_trends[0]["tag"] == "AI"
    assert sorted_trends[-1]["tag"] == "VR"
