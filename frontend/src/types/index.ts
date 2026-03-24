// ==================== 用户与认证 ====================

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: 'admin' | 'member';
  is_active: boolean;
  last_active_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

// ==================== 文章 ====================

export interface Article {
  id: string;
  url: string;
  title: string;
  content_snippet: string | null;
  summary: string | null;
  summary_zh: string | null;
  language: string | null;
  author: string | null;
  published_at: string | null;
  processing_status: string;
  source: SourceBrief;
  categories: ArticleCategoryInfo[];
  tags: ArticleTagInfo[];
  is_bookmarked?: boolean;
  is_read?: boolean;
  comment_count?: number;
}

export interface SourceBrief {
  id: string;
  name: string;
  type: string;
}

export interface ArticleCategoryInfo {
  category_id: string;
  name: string;
  name_zh: string | null;
  confidence_score: number;
}

export interface ArticleTagInfo {
  tag_id: string;
  canonical_name: string;
}

export interface PaginatedArticles {
  articles: Article[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Comment {
  id: string;
  user_id: string;
  user_display_name: string;
  content: string;
  created_at: string;
}

// ==================== 分类与标签 ====================

export interface Category {
  id: string;
  name: string;
  name_zh: string | null;
  slug: string;
  is_active: boolean;
  display_order: number;
  article_count?: number;
}

export interface Tag {
  tag_id: string;
  canonical_name: string;
  article_count: number;
}

export interface TagCloudItem {
  tag_id: string;
  canonical_name: string;
  count: number;
  weight: number;
}

// ==================== 数据源 ====================

export interface Source {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  cron_interval: number;
  is_enabled: boolean;
  status: 'active' | 'degraded' | 'disabled';
  last_collected_at: string | null;
  consecutive_failures: number;
  article_count?: number;
}

export interface CollectionLog {
  id: string;
  source_id: string;
  started_at: string;
  completed_at: string | null;
  articles_fetched: number;
  status: 'success' | 'failed' | 'partial';
  error_message: string | null;
}

// ==================== 趋势 ====================

export interface TrendingTopic {
  tag_id: string;
  tag_name: string;
  current_count: number;
  previous_count: number;
  growth_rate: number;
  is_new_topic: boolean;
}

export interface TimeseriesPoint {
  date: string;
  count: number;
}

export interface CategoryDistribution {
  category_id: string;
  category_name: string;
  category_name_zh: string | null;
  count: number;
  percentage: number;
}

export interface TrendDigest {
  id: string;
  week_start: string;
  content: string;
  generated_at: string | null;
}
