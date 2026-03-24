import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Filter, X } from 'lucide-react';
import clsx from 'clsx';
import api from '../services/api';
import type { Category, Source as SourceType } from '../types';

interface FilterBarProps {
  onFilterChange: (filters: FilterState) => void;
}

export interface FilterState {
  category_ids: string[];
  source_ids: string[];
  language: string;
  date_from: string;
  date_to: string;
  sort: 'latest' | 'relevant';
}

const EMPTY_FILTERS: FilterState = {
  category_ids: [],
  source_ids: [],
  language: '',
  date_from: '',
  date_to: '',
  sort: 'latest',
};

export default function FilterBar({ onFilterChange }: FilterBarProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState<Category[]>([]);
  const [sources, setSources] = useState<SourceType[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  // 从 URL 参数初始化筛选状态
  const [filters, setFilters] = useState<FilterState>(() => ({
    category_ids: searchParams.get('categories')?.split(',').filter(Boolean) || [],
    source_ids: searchParams.get('sources')?.split(',').filter(Boolean) || [],
    language: searchParams.get('lang') || '',
    date_from: searchParams.get('from') || '',
    date_to: searchParams.get('to') || '',
    sort: (searchParams.get('sort') as 'latest' | 'relevant') || 'latest',
  }));

  // 加载分类和数据源列表
  useEffect(() => {
    api.get('/categories').then((res) => setCategories(res.data.categories || [])).catch(() => {});
    api.get('/admin/sources').then((res) => setSources(res.data.sources || [])).catch(() => {});
  }, []);

  // 同步筛选到 URL 和父组件
  const applyFilters = useCallback(
    (newFilters: FilterState) => {
      setFilters(newFilters);
      onFilterChange(newFilters);

      // 持久化到 URL
      const params = new URLSearchParams();
      if (newFilters.category_ids.length) params.set('categories', newFilters.category_ids.join(','));
      if (newFilters.source_ids.length) params.set('sources', newFilters.source_ids.join(','));
      if (newFilters.language) params.set('lang', newFilters.language);
      if (newFilters.date_from) params.set('from', newFilters.date_from);
      if (newFilters.date_to) params.set('to', newFilters.date_to);
      if (newFilters.sort !== 'latest') params.set('sort', newFilters.sort);
      setSearchParams(params, { replace: true });
    },
    [onFilterChange, setSearchParams]
  );

  const toggleCategory = (id: string) => {
    const next = filters.category_ids.includes(id)
      ? filters.category_ids.filter((c) => c !== id)
      : [...filters.category_ids, id];
    applyFilters({ ...filters, category_ids: next });
  };

  const clearFilters = () => applyFilters(EMPTY_FILTERS);

  const hasActiveFilters =
    filters.category_ids.length > 0 ||
    filters.source_ids.length > 0 ||
    filters.language ||
    filters.date_from ||
    filters.date_to;

  return (
    <div className="mb-4">
      {/* 切换按钮 + 排序 */}
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
            isOpen || hasActiveFilters
              ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
          )}
        >
          <Filter size={14} />
          筛选
          {hasActiveFilters && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-primary-600 text-white text-[10px]">
              {filters.category_ids.length + filters.source_ids.length + (filters.language ? 1 : 0)}
            </span>
          )}
        </button>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-500 hover:text-red-500 transition-colors"
          >
            <X size={12} />
            清除
          </button>
        )}

        <div className="ml-auto flex gap-1">
          {(['latest', 'relevant'] as const).map((s) => (
            <button
              key={s}
              onClick={() => applyFilters({ ...filters, sort: s })}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                filters.sort === s
                  ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
              )}
            >
              {s === 'latest' ? '最新' : '最相关'}
            </button>
          ))}
        </div>
      </div>

      {/* 展开的筛选面板 */}
      {isOpen && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
          {/* 分类 */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">分类</label>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => toggleCategory(cat.id)}
                  className={clsx(
                    'px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
                    filters.category_ids.includes(cat.id)
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200'
                  )}
                >
                  {cat.name_zh || cat.name}
                </button>
              ))}
            </div>
          </div>

          {/* 语言 + 日期 */}
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">语言</label>
              <select
                value={filters.language}
                onChange={(e) => applyFilters({ ...filters, language: e.target.value })}
                className="px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm"
              >
                <option value="">全部</option>
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">日期范围</label>
              <div className="flex gap-2 items-center">
                <input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => applyFilters({ ...filters, date_from: e.target.value })}
                  className="px-2 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm"
                />
                <span className="text-gray-400 text-sm">~</span>
                <input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => applyFilters({ ...filters, date_to: e.target.value })}
                  className="px-2 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
