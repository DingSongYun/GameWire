import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, Inbox } from 'lucide-react';
import api from '../services/api';
import ArticleCard from '../components/ArticleCard';
import FilterBar, { type FilterState } from '../components/FilterBar';
import ArticleDetailModal from '../components/ArticleDetailModal';
import type { Article } from '../types';

export default function FeedPage() {
  const [searchParams] = useSearchParams();
  const [articles, setArticles] = useState<Article[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    category_ids: [],
    source_ids: [],
    language: '',
    date_from: '',
    date_to: '',
    sort: 'latest',
  });
  const observerRef = useRef<HTMLDivElement | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // 获取文章列表
  const fetchArticles = useCallback(
    async (pageNum: number, append = false) => {
      setIsLoading(true);
      try {
        const params: Record<string, string> = {
          page: String(pageNum),
          page_size: '20',
        };
        if (filters.category_ids.length) params.category_ids = filters.category_ids.join(',');
        if (filters.source_ids.length) params.source_ids = filters.source_ids.join(',');
        if (filters.language) params.language = filters.language;
        if (filters.date_from) params.date_from = filters.date_from;
        if (filters.date_to) params.date_to = filters.date_to;

        let res;
        if (searchQuery.trim()) {
          res = await api.get('/articles/search', {
            params: { q: searchQuery, ...params, sort: filters.sort === 'relevant' ? 'relevance' : 'date' },
          });
        } else {
          res = await api.get('/articles', { params });
        }

        const data = res.data;
        setTotalPages(data.total_pages || 1);
        if (append) {
          setArticles((prev) => [...prev, ...(data.articles || [])]);
        } else {
          setArticles(data.articles || []);
        }
      } catch (err) {
        console.error('获取文章失败:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [filters, searchQuery]
  );

  // 初始加载和筛选变化时重新加载
  useEffect(() => {
    setPage(1);
    fetchArticles(1, false);
  }, [fetchArticles]);

  // 无限滚动 — IntersectionObserver
  useEffect(() => {
    if (!observerRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isLoading && page < totalPages) {
          const nextPage = page + 1;
          setPage(nextPage);
          fetchArticles(nextPage, true);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(observerRef.current);
    return () => observer.disconnect();
  }, [page, totalPages, isLoading, fetchArticles]);

  // 搜索防抖
  const handleSearchInput = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchQuery(value);
    }, 400);
  };

  // 收藏切换
  const handleBookmarkToggle = async (articleId: string, bookmark: boolean) => {
    try {
      if (bookmark) {
        await api.post(`/articles/${articleId}/bookmark`);
      } else {
        await api.delete(`/articles/${articleId}/bookmark`);
      }
      setArticles((prev) =>
        prev.map((a) => (a.id === articleId ? { ...a, is_bookmarked: bookmark } : a))
      );
    } catch (err) {
      console.error('收藏操作失败:', err);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">信息流</h1>

      {/* 筛选栏 */}
      <FilterBar onFilterChange={setFilters} />

      {/* 文章列表 */}
      {articles.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <Inbox size={48} className="mb-4" />
          <p className="text-lg">暂无文章</p>
          <p className="text-sm">等待数据源采集或调整筛选条件</p>
        </div>
      ) : (
        <div className="space-y-3">
          {articles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              onBookmarkToggle={handleBookmarkToggle}
              onClick={setSelectedArticle}
            />
          ))}
        </div>
      )}

      {/* 无限滚动触发点 */}
      <div ref={observerRef} className="h-10 flex items-center justify-center mt-4">
        {isLoading && <Loader2 size={24} className="animate-spin text-primary-600" />}
        {!isLoading && page >= totalPages && articles.length > 0 && (
          <p className="text-sm text-gray-400">已加载全部文章</p>
        )}
      </div>

      {/* 文章详情弹窗 */}
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