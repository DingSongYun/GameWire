import clsx from 'clsx';
import type { TagCloudItem } from '../types';

interface TagCloudProps {
  tags: TagCloudItem[];
  onTagClick?: (tagId: string) => void;
}

// 根据权重映射字体大小
function getFontSize(weight: number): string {
  if (weight >= 0.8) return 'text-xl font-bold';
  if (weight >= 0.6) return 'text-lg font-semibold';
  if (weight >= 0.4) return 'text-base font-medium';
  if (weight >= 0.2) return 'text-sm';
  return 'text-xs';
}

const TAG_COLORS = [
  'text-blue-600 dark:text-blue-400',
  'text-purple-600 dark:text-purple-400',
  'text-green-600 dark:text-green-400',
  'text-orange-600 dark:text-orange-400',
  'text-pink-600 dark:text-pink-400',
  'text-cyan-600 dark:text-cyan-400',
  'text-red-600 dark:text-red-400',
  'text-amber-600 dark:text-amber-400',
];

export default function TagCloud({ tags, onTagClick }: TagCloudProps) {
  if (tags.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 text-center text-gray-400 text-sm">
        暂无标签数据
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold mb-3">标签云</h3>
      <div className="flex flex-wrap gap-2 items-center justify-center py-4">
        {tags.map((tag, index) => (
          <button
            key={tag.tag_id}
            onClick={() => onTagClick?.(tag.tag_id)}
            className={clsx(
              'px-2 py-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer',
              getFontSize(tag.weight),
              TAG_COLORS[index % TAG_COLORS.length]
            )}
            title={`${tag.canonical_name}: ${tag.count} 篇`}
          >
            {tag.canonical_name}
          </button>
        ))}
      </div>
    </div>
  );
}
