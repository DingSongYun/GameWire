import { Sparkles } from 'lucide-react';
import type { TrendDigest } from '../types';

interface WeeklyDigestProps {
  digest: TrendDigest;
  isNew: boolean;
}

export default function WeeklyDigest({ digest, isNew }: WeeklyDigestProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={18} className="text-amber-500" />
        <h2 className="text-sm font-semibold">每周趋势摘要</h2>
        <span className="text-xs text-gray-400">{digest.week_start} 周报</span>
        {isNew && (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">
            新
          </span>
        )}
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
        {digest.content}
      </div>
      {digest.generated_at && (
        <p className="mt-3 text-xs text-gray-400">
          生成于 {new Date(digest.generated_at).toLocaleDateString('zh-CN')}
        </p>
      )}
    </div>
  );
}
