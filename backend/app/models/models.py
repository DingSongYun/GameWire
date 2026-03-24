import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ==================== 枚举类型 ====================


class SourceType(str, enum.Enum):
    RSS = "rss"
    TWITTER = "twitter"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    WEBSCRAPER = "webscraper"
    GITHUB = "github"


class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    CLEANING = "cleaning"
    DEDUP = "dedup"
    LANGUAGE = "language"
    SUMMARIZING = "summarizing"
    CLASSIFYING = "classifying"
    TRANSLATING = "translating"
    DONE = "done"
    FAILED = "failed"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class CollectionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# ==================== 数据源模型 ====================


class Source(TimestampMixin, Base):
    """数据源配置"""
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cron_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=30)  # 分钟
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus), default=SourceStatus.ACTIVE, nullable=False
    )
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    articles: Mapped[list["Article"]] = relationship(back_populates="source", lazy="selectin")
    collection_logs: Mapped[list["CollectionLog"]] = relationship(back_populates="source", lazy="selectin")


# ==================== 文章模型 ====================


class Article(TimestampMixin, Base):
    """文章"""
    __tablename__ = "articles"

    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clean_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    author: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    simhash_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False
    )
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # 关系
    source: Mapped["Source"] = relationship(back_populates="articles", lazy="selectin")
    categories: Mapped[list["ArticleCategory"]] = relationship(back_populates="article", lazy="selectin")
    tags: Mapped[list["ArticleTag"]] = relationship(back_populates="article", lazy="selectin")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="article", lazy="selectin")
    comments: Mapped[list["Comment"]] = relationship(back_populates="article", lazy="selectin")
    read_statuses: Mapped[list["ReadStatus"]] = relationship(back_populates="article", lazy="selectin")


# ==================== 分类模型 ====================


class Category(TimestampMixin, Base):
    """文章分类"""
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name_zh: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    article_categories: Mapped[list["ArticleCategory"]] = relationship(back_populates="category", lazy="selectin")


# ==================== 标签模型 ====================


class Tag(TimestampMixin, Base):
    """文章标签"""
    __tablename__ = "tags"

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    aliases: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)

    # 关系
    article_tags: Mapped[list["ArticleTag"]] = relationship(back_populates="tag", lazy="selectin")
    frequencies: Mapped[list["TagFrequency"]] = relationship(back_populates="tag", lazy="selectin")


# ==================== 关联表 ====================


class ArticleCategory(Base):
    """文章-分类关联表"""
    __tablename__ = "article_categories"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # 关系
    article: Mapped["Article"] = relationship(back_populates="categories", lazy="selectin")
    category: Mapped["Category"] = relationship(back_populates="article_categories", lazy="selectin")


class ArticleTag(Base):
    """文章-标签关联表"""
    __tablename__ = "article_tags"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    # 关系
    article: Mapped["Article"] = relationship(back_populates="tags", lazy="selectin")
    tag: Mapped["Tag"] = relationship(back_populates="article_tags", lazy="selectin")


# ==================== 用户模型 ====================


class User(TimestampMixin, Base):
    """用户"""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关系
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user", lazy="selectin")
    comments: Mapped[list["Comment"]] = relationship(back_populates="user", lazy="selectin")
    read_statuses: Mapped[list["ReadStatus"]] = relationship(back_populates="user", lazy="selectin")


# ==================== 协作模型 ====================


class Bookmark(Base):
    """文章收藏"""
    __tablename__ = "bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_bookmark_user_article"),)

    # 关系
    user: Mapped["User"] = relationship(back_populates="bookmarks", lazy="selectin")
    article: Mapped["Article"] = relationship(back_populates="bookmarks", lazy="selectin")


class Comment(TimestampMixin, Base):
    """文章评论"""
    __tablename__ = "comments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 关系
    user: Mapped["User"] = relationship(back_populates="comments", lazy="selectin")
    article: Mapped["Article"] = relationship(back_populates="comments", lazy="selectin")


class ReadStatus(Base):
    """阅读状态（复合主键）"""
    __tablename__ = "read_statuses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 关系
    user: Mapped["User"] = relationship(back_populates="read_statuses", lazy="selectin")
    article: Mapped["Article"] = relationship(back_populates="read_statuses", lazy="selectin")


# ==================== 趋势分析模型 ====================


class TagFrequency(Base):
    """标签频率统计（用于趋势聚合）"""
    __tablename__ = "tag_frequencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_tag_freq_tag_date", "tag_id", "date"),
        UniqueConstraint("tag_id", "category_id", "date", name="uq_tag_freq"),
    )

    # 关系
    tag: Mapped["Tag"] = relationship(back_populates="frequencies", lazy="selectin")


class TrendDigest(Base):
    """每周趋势摘要"""
    __tablename__ = "trend_digests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ==================== 采集日志模型 ====================


class CollectionLog(Base):
    """采集日志"""
    __tablename__ = "collection_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    articles_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[CollectionStatus] = mapped_column(Enum(CollectionStatus), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_collection_log_source_started", "source_id", "started_at"),)

    # 关系
    source: Mapped["Source"] = relationship(back_populates="collection_logs", lazy="selectin")
