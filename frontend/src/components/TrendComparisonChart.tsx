import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../services/api';

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];

interface TrendComparisonChartProps {
  tagIds: string[];
  days: number;
}

interface MergedPoint {
  date: string;
  [key: string]: string | number;
}

export default function TrendComparisonChart({ tagIds, days }: TrendComparisonChartProps) {
  const [data, setData] = useState<MergedPoint[]>([]);
  const [tagNames, setTagNames] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (tagIds.length < 2) return;
    setIsLoading(true);
    api
      .get('/trends/compare', { params: { tag_ids: tagIds.join(','), days } })
      .then((res) => {
        const series: Record<string, { date: string; count: number }[]> = res.data.series || {};
        const names: Record<string, string> = res.data.tag_names || {};
        setTagNames(names);

        // 合并所有日期到统一数据点
        const dateMap: Record<string, MergedPoint> = {};
        for (const [tagId, points] of Object.entries(series)) {
          for (const p of points) {
            if (!dateMap[p.date]) dateMap[p.date] = { date: p.date };
            dateMap[p.date][tagId] = p.count;
          }
        }
        const merged = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
        setData(merged);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [tagIds, days]);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 text-center text-gray-400 text-sm">
        加载对比数据...
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold mb-3">话题对比</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
            formatter={(value: number, name: string) => [value, tagNames[name] || name]}
            labelFormatter={(label) => `日期: ${label}`}
          />
          <Legend formatter={(value) => tagNames[value] || value} />
          {tagIds.map((tagId, i) => (
            <Line
              key={tagId}
              type="monotone"
              dataKey={tagId}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
