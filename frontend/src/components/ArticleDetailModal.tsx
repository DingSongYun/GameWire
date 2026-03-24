import { useState, useEffect } from 'react';
import { X, ExternalLink, Languages, Bookmark, BookmarkCheck } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import api from '../services/api';
import CommentSection from './CommentSection';
import type { Article } from '../types';

interface ArticleDetailModalProps {
  article: Article;
  onClose: () => void;
  onBookmarkToggle?: (articleId: string, isBookmarked: boolean) => void;
}

export default function ArticleDetailModal({ article, onClose, onBookmarkToggle }: ArticleDetailModalProps) {
  const [translatedSummary, setTranslatedSummary] = useState<string | null>(article.summary_zh);
  const [isTranslating, setIsTranslating] = useState(false);

  // 标记为已读
  useEffect(() => {
    api.post(`/articles/${article.id}/read`).catch(() => {});
  }, [article.id]);

  // 按需翻译
  const handleTranslate = async () => {
    setIsTranslating(true);
    try {
      const { data } = await api.post(`/articles/${article.id}/translate`);
      setTranslatedSummary(data.summary_zh || data.translated_summary);
    } catch {
      // 静默失败
    } finally {
      setIsTranslating(false);
    }
  };

  const publishedAt = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true, locale: zhCN })
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 pb-8">
      {/* 背景遮罩 */}
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />

      {/* 弹窗内容 */}
      <div className="relative w-full max-w-2xl max-h-full overflow-y-auto bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 mx-4">
        {/* 头部 */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-start justify-between z-10">
          <div className="flex-1 pr-4">
            <h2 className="text-lg font-bold leading-snug">{article.title}</h2>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium">{article.source?.name}</span>
              {article.author && (
                <>
                  <span>·</span>
                  <span>{article.author}</span>
                </>
              )}
              {publishedAt && (
                <>
                  <span>·</span>
                  <span>{publishedAt}</span>
                </>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* 分类和标签 */}
          <div className="flex flex-wrap gap-1.5">
            {article.categories?.map((cat) => (
              <span
                key={cat.category_id}
                className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
              >
                {cat.name_zh || cat.name}
              </span>
            ))}
            {article.tags?.map((tag) => (
              <span
                key={tag.tag_id}
                className="px-1.5 py-0.5 rounded text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700"
              >
                #{tag.canonical_name}
              </span>
            ))}
          </div>

          {/* 摘要 */}
          <div>
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1">摘要</h3>
            <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
              {article.summary || article.content_snippet || '暂无摘要'}
            </p>
          </div>

          {/* 翻译摘要 */}
          {translatedSummary && (
            <div>
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1">中文翻译</h3>
              <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                {translatedSummary}
              </p>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex items-center gap-3 pt-2">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium transition-colors"
            >
              <ExternalLink size={14} />
              查看原文
            </a>

            {!translatedSummary && article.language !== 'zh' && (
              <button
                onClick={handleTranslate}
                disabled={isTranslating}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                <Languages size={14} />
                {isTranslating ? '翻译中...' : '翻译为中文'}
              </button>
            )}

            <button
              onClick={() => onBookmarkToggle?.(article.id, !article.is_bookmarked)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              {article.is_bookmarked ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
              {article.is_bookmarked ? '已收藏' : '收藏'}
            </button>
          </div>

          {/* 评论区域 */}
          <CommentSection articleId={article.id} />
        </div>
      </div>
    </div>
  );
}
