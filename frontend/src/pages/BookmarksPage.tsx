import { useState, useEffect } from 'react';
import { Inbox, Loader2 } from 'lucide-react';
import api from '../services/api';
import ArticleCard from '../components/ArticleCard';
import ArticleDetailModal from '../components/ArticleDetailModal';
import type { Article } from '../types';

export default function BookmarksPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const fetchBookmarks = async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get('/me/bookmarks');
      setArticles(data.articles || []);
    } catch {
      // 静默
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBookmarks();
  }, []);

  const handleBookmarkToggle = async (articleId: string, bookmark: boolean) => {
    try {
      if (bookmark) {
        await api.post(`/articles/${articleId}/bookmark`);
      } else {
        await api.delete(`/articles/${articleId}/bookmark`);
        // 从列表中移除
        setArticles((prev) => prev.filter((a) => a.id !== articleId));
      }
    } catch (err) {
      console.error('收藏操作失败:', err);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">我的收藏</h1>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={32} className="animate-spin text-primary-600" />
        </div>
      ) : articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <Inbox size={48} className="mb-4" />
          <p className="text-lg">暂无收藏</p>
          <p className="text-sm">浏览信息流时点击收藏按钮添加</p>
        </div>
      ) : (
        <div className="space-y-3">
          {articles.map((article) => (
            <ArticleCard
              key={article.id}
              article={{ ...article, is_bookmarked: true }}
              onBookmarkToggle={handleBookmarkToggle}
              onClick={setSelectedArticle}
            />
          ))}
        </div>
      )}

      {selectedArticle && (
        <ArticleDetailModal
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
          onBookmarkToggle={handleBookmarkToggle}
        />
      )}
    </div>
  );
}