"""适配器注册表和自动发现机制"""
import logging
from typing import Any

from app.adapters.base import SourceAdapter
from app.models.models import SourceType

logger = logging.getLogger(__name__)

# 全局适配器注册表：SourceType → SourceAdapter 子类
_adapter_registry: dict[SourceType, type[SourceAdapter]] = {}


def register_adapter(adapter_cls: type[SourceAdapter]) -> type[SourceAdapter]:
    """装饰器：将适配器类注册到全局注册表"""
    if not hasattr(adapter_cls, "source_type"):
        raise ValueError(f"{adapter_cls.__name__} 缺少 source_type 属性")
    _adapter_registry[adapter_cls.source_type] = adapter_cls
    logger.info(f"已注册适配器: {adapter_cls.source_type.value} → {adapter_cls.__name__}")
    return adapter_cls


def get_adapter(source_type: SourceType, config: dict[str, Any]) -> SourceAdapter:
    """根据数据源类型获取适配器实例"""
    adapter_cls = _adapter_registry.get(source_type)
    if adapter_cls is None:
        raise ValueError(f"未注册的数据源类型: {source_type.value}")
    return adapter_cls(config)


def get_registered_types() -> list[SourceType]:
    """返回所有已注册的数据源类型"""
    return list(_adapter_registry.keys())


def discover_adapters() -> None:
    """自动发现并导入所有适配器模块，触发 @register_adapter 注册"""
    # 导入所有适配器模块 — 模块级的 @register_adapter 装饰器会自动注册
    from app.adapters import (  # noqa: F401
        github_adapter,
        hackernews_adapter,
        reddit_adapter,
        rss_adapter,
        twitter_adapter,
        webscraper_adapter,
    )
    logger.info(f"适配器发现完成，共注册 {len(_adapter_registry)} 个适配器")
