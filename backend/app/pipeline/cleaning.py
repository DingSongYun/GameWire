"""内容清洗模块：剥离 HTML、移除追踪参数、规范化空白"""
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

# 需要移除的 URL 追踪参数
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source",
}


def strip_html(html: str) -> str:
    """剥离 HTML 标签，保留有意义的文本结构"""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # 移除 script 和 style 标签
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # 获取文本，保留段落换行
    lines = []
    for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "li", "div", "span", "td"]):
        text = element.get_text(strip=True)
        if text:
            lines.append(text)

    if not lines:
        # 回退：直接获取所有文本
        return normalize_whitespace(soup.get_text(separator=" ", strip=True))

    return "\n".join(lines)


def remove_tracking_params(url: str) -> str:
    """移除 URL 中的追踪参数"""
    if not url:
        return url

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        cleaned = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
        clean_query = urlencode(cleaned, doseq=True)
        return urlunparse(parsed._replace(query=clean_query))
    except Exception:
        return url


def normalize_whitespace(text: str) -> str:
    """规范化空白字符"""
    if not text:
        return ""

    # 替换多个空白为单个空格
    text = re.sub(r"[ \t]+", " ", text)
    # 替换多个换行为两个换行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_content(content: str | None, url: str | None = None) -> tuple[str, str | None]:
    """
    完整的内容清洗管线。

    Returns:
        tuple[str, str | None]: (清洗后的内容, 清洗后的 URL)
    """
    cleaned_text = ""
    if content:
        cleaned_text = strip_html(content)
        cleaned_text = normalize_whitespace(cleaned_text)

    cleaned_url = remove_tracking_params(url) if url else url

    return cleaned_text, cleaned_url
