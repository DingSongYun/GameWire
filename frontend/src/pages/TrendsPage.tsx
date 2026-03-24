```typescript jsx filePath=src/pages/TrendsPage.tsx
import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import api from '../services/api';
import TrendingTopicsList from '../components/TrendingTopicsList';
import TrendLineChart from '../components/TrendLineChart';
import TrendComparisonChart from '../components/TrendComparisonChart';
import CategoryDistributionChart from '../components/CategoryDistributionChart';
import TagCloud from '../components/TagCloud';
import WeeklyDigest from '../components/WeeklyDigest';
import type { TrendingTopic, TimeseriesPoint, CategoryDistribution, TagCloudItem, TrendDigest } from '../types';

export default function TrendsPage() {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [distribution, setDistribution] = useState<CategoryDistribution[]>([]);
  const [tagCloud, setTagCloud] = useState<TagCloudItem[]>([]);
  const [digest, setDigest] = useState<TrendDigest | null>(null);
  const [isDigestNew, setIsDigestNew] = useState(false);
  const [selectedTagId, setSelectedTagId] = useState<string | null>(null);
  const [compareTagIds, setCompareTagIds] = useState<string[]>([]);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [timeRange, setTimeRange] = useState<7 | 30 | 90>(30);
  const [isLoading, setIsLoading] = useState(true);

  // 初始加载
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const [topicsRes, distRes, cloudRes, digestRes] = await Promise.all([
          api.get('/trends/topics'),
          api.get('/trends/distribution', { params: { days: 7 } }),
          api.get('/tags/cloud', { params: { limit: 40 } }),
          api.get('/trends/digests/latest'),
        ]);
        setTopics(topicsRes.data.topics || []);
        setDistribution(distRes.data.categories || []);
        setTagCloud(cloudRes.data.tags || []);
        setDigest(digestRes.data.digest || null);
        setIsDigestNew(digestRes.data.is_new || false);
      } catch (err) {
        console.error('加载趋势数据失败:', err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  // 加载单个话题时间序列
  useEffect(() => {
    if (!selectedTagId) {
      setTimeseries([]);
      return;
    }
    api
      .get(`/trends/topic/${selectedTagId}/timeseries`, { params: { days: timeRange } })
      .then((res) => setTimeseries(res.data.data || []))
      .catch(() => setTimeseries([]));
  }, [selectedTagId, timeRange]);

  // 话题点击 → 切换选中
  const handleTopicClick = (tagId: string) => {
    if (selectedTagId === tagId) {
      setSelectedTagId(null);
    } else {
      setSelectedTagId(tagId);
    }
  };

  // 对比模式切换
  const handleCompareToggle = (tagId: string) => {
    setCompareTagIds((prev) => {
      if (prev.includes(tagId)) return prev.filter((id) => id !== tagId);
      if (prev.length >= 5) return prev;
      return [...prev, tagId];
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 size={32} className="animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">趋势分析</h1>

      {/* 每周摘要 */}
      {digest && <WeeklyDigest digest={digest} isNew={isDigestNew} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧: 趋势话题列表 */}
        <div className="lg:col-span-1">
          <TrendingTopicsList
            topics={topics}
            selectedId={selectedTagId}
            compareIds={compareTagIds}
            onTopicClick={handleTopicClick}
            onCompareToggle={handleCompareToggle}
          />
        </div>

        {/* 右侧: 图表区域 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 时间范围切换 */}
          <div className="flex gap-1">
            {([7, 30, 90] as const).map((d) => (
              <button
                key={d}
                onClick={() => setTimeRange(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  timeRange === d
                    ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                    : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                }`}
              >
                {d}天
              </button>
            ))}
          </div>

          {/* 单话题折线图 */}
          {selectedTagId && compareTagIds.length < 2 && (
            <TrendLineChart
              data={timeseries}
              tagName={topics.find((t) => t.tag_id === selectedTagId)?.tag_name || ''}
            />
          )}

          {/* 多话题对比图 */}
          {compareTagIds.length >= 2 && (
            <TrendComparisonChart tagIds={compareTagIds} days={timeRange} />
          )}

          {/* 分类分布 */}
          <CategoryDistributionChart data={distribution} />

          {/* 标签云 */}
          <TagCloud tags={tagCloud} onTagClick={(tagId) => handleTopicClick(tagId)} />
        </div>
      </div>
    </div>
  );
}
```