import { Bookmark, BookmarkCheck, MessageSquare, ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import clsx from 'clsx';
import type { Article } from '../types';

// 分类颜色映射
const CATEGORY_COLORS: Record<string, string> = {
  'AI 技术': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  '游戏引擎': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  '行业新闻': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  '市场动态': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  '开发工具': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  '图形渲染': 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  '网络技术': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  '公司动态': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const DEFAULT_CATEGORY_COLOR = 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';

// 数据源类型颜色
const SOURCE_TYPE_COLORS: Record<string, string> = {
  rss: 'text-orange-500',
  twitter: 'text-sky-500',
  reddit: 'text-orange-600',
  hackernews: 'text-amber-600',
  github: 'text-gray-800 dark:text-gray-200',
  webscraper: 'text-green-600',
};

interface ArticleCardProps {
  article: Article;
  onBookmarkToggle?: (articleId: string, isBookmarked: boolean) => void;
  onClick?: (article: Article) => void;
}

export default function ArticleCard({ article, onBookmarkToggle, onClick }: ArticleCardProps) {
  const publishedAt = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true, locale: zhCN })
    : null;

  const summary = article.summary_zh || article.summary || article.content_snippet;
  const truncatedSummary = summary && summary.length > 150 ? summary.slice(0, 150) + '...' : summary;

  return (
    <div
      className={clsx(
        'bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow cursor-pointer',
        !article.is_read && 'border-l-4 border-l-primary-500'
      )}
      onClick={() => onClick?.(article)}
    >
      {/* 顶部: 来源 + 时间 */}
      <div className="flex items-center gap-2 mb-2 text-xs">
        <span className={clsx('font-medium', SOURCE_TYPE_COLORS[article.source?.type] || 'text-gray-500')}>
          {article.source?.name || '未知来源'}
        </span>
        {article.author && (
          <>
            <span className="text-gray-300 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-400">{article.author}</span>
          </>
        )}
        {publishedAt && (
          <>
            <span className="text-gray-300 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-400">{publishedAt}</span>
          </>
        )}
        {article.language && (
          <span className="ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 uppercase">
            {article.language}
          </span>
        )}
      </div>

      {/* 标题 */}
      <h3 className="text-base font-semibold mb-2 line-clamp-2 leading-snug">
        {article.title}
      </h3>

      {/* 摘要 */}
      {truncatedSummary && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-3">
          {truncatedSummary}
        </p>
      )}

      {/* 分类标签 */}
      {article.categories && article.categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {article.categories.map((cat) => (
            <span
              key={cat.category_id}
              className={clsx(
                'px-2 py-0.5 rounded-full text-xs font-medium',
                CATEGORY_COLORS[cat.name_zh || cat.name] || DEFAULT_CATEGORY_COLOR
              )}
            >
              {cat.name_zh || cat.name}
            </span>
          ))}
        </div>
      )}

      {/* 标签 */}
      {article.tags && article.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {article.tags.slice(0, 5).map((tag) => (
            <span
              key={tag.tag_id}
              className="px-1.5 py-0.5 rounded text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50"
            >
              #{tag.canonical_name}
            </span>
          ))}
          {article.tags.length > 5 && (
            <span className="text-xs text-gray-400">+{article.tags.length - 5}</span>
          )}
        </div>
      )}

      {/* 底部操作栏 */}
      <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-700">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onBookmarkToggle?.(article.id, !article.is_bookmarked);
          }}
          className={clsx(
            'flex items-center gap-1 text-xs transition-colors',
            article.is_bookmarked
              ? 'text-primary-600 dark:text-primary-400'
              : 'text-gray-400 hover:text-primary-600 dark:hover:text-primary-400'
          )}
        >
          {article.is_bookmarked ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
          {article.is_bookmarked ? '已收藏' : '收藏'}
        </button>

        <div className="flex items-center gap-1 text-xs text-gray-400">
          <MessageSquare size={14} />
          <span>{article.comment_count || 0}</span>
        </div>

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 ml-auto transition-colors"
        >
          <ExternalLink size={14} />
          原文
        </a>
      </div>
    </div>
  );
}
