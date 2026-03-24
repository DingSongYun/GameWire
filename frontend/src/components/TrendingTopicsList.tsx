import { TrendingUp, Plus, Check } from 'lucide-react';
import clsx from 'clsx';
import type { TrendingTopic } from '../types';

interface TrendingTopicsListProps {
  topics: TrendingTopic[];
  selectedId: string | null;
  compareIds: string[];
  onTopicClick: (tagId: string) => void;
  onCompareToggle: (tagId: string) => void;
}

export default function TrendingTopicsList({
  topics,
  selectedId,
  compareIds,
  onTopicClick,
  onCompareToggle,
}: TrendingTopicsListProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h2 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
        <TrendingUp size={16} className="text-primary-600" />
        趋势话题 Top 20
      </h2>

      {topics.length === 0 ? (
        <p className="text-sm text-gray-400 py-4 text-center">暂无趋势数据</p>
      ) : (
        <div className="space-y-1">
          {topics.map((topic, index) => (
            <div
              key={topic.tag_id}
              className={clsx(
                'flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-colors text-sm',
                selectedId === topic.tag_id
                  ? 'bg-primary-50 dark:bg-primary-900/30'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
              )}
              onClick={() => onTopicClick(topic.tag_id)}
            >
              {/* 排名 */}
              <span className="text-xs font-bold text-gray-400 w-5 text-right">{index + 1}</span>

              {/* 话题名 */}
              <span className="flex-1 font-medium truncate">{topic.tag_name}</span>

              {/* 增长徽章 */}
              <span
                className={clsx(
                  'px-1.5 py-0.5 rounded text-[11px] font-bold',
                  topic.is_new_topic
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : topic.growth_rate >= 1
                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                )}
              >
                {topic.is_new_topic ? '🆕 新' : `↑${Math.round(topic.growth_rate * 100)}%`}
              </span>

              {/* 数量 */}
              <span className="text-xs text-gray-400 w-8 text-right">{topic.current_count}</span>

              {/* 对比按钮 */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCompareToggle(topic.tag_id);
                }}
                className={clsx(
                  'p-1 rounded transition-colors',
                  compareIds.includes(topic.tag_id)
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-300 hover:text-primary-600 dark:text-gray-600 dark:hover:text-primary-400'
                )}
                title="加入对比"
              >
                {compareIds.includes(topic.tag_id) ? <Check size={12} /> : <Plus size={12} />}
              </button>
            </div>
          ))}
        </div>
      )}

      {compareIds.length > 0 && (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          已选 {compareIds.length}/5 个话题对比
        </p>
      )}
    </div>
  );
}
