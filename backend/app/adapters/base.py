"""数据源适配器抽象基类和统一文章模型"""
import abc
import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.models import SourceType

logger = logging.getLogger(__name__)


class RawArticle(BaseModel):
    """统一的原始文章模型 — 所有适配器的输出必须符合此 Schema"""

    title: str
    url: str
    content_snippet: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    source_name: str
    raw_metadata: Optional[dict[str, Any]] = Field(default_factory=dict)


class SourceAdapter(abc.ABC):
    """数据源适配器抽象基类"""

    # 子类必须声明其对应的数据源类型
    source_type: SourceType

    def __init__(self, config: dict[str, Any]):
        """
        Args:
            config: 数据源特定的配置（从 Source.config JSONB 字段加载）
        """
        self.config = config

    @abc.abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """
        从数据源抓取内容，返回统一格式的文章列表。

        Returns:
            list[RawArticle]: 抓取到的文章列表
        Raises:
            Exception: 抓取过程中遇到的任何错误
        """
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """
        检查数据源是否可用。

        Returns:
            bool: True 表示数据源可用
        """
        ...

    def get_source_name(self) -> str:
        """返回数据源显示名称"""
        return self.config.get("name", self.source_type.value)
