import { useState, useEffect } from 'react';
import { Plus, RefreshCw, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import clsx from 'clsx';
import api from '../services/api';
import type { Source, CollectionLog } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

// ─── 数据源类型配置模板 ───
const SOURCE_TYPE_OPTIONS = [
  { value: 'rss', label: 'RSS 订阅' },
  { value: 'twitter', label: 'Twitter/X' },
  { value: 'reddit', label: 'Reddit' },
  { value: 'hackernews', label: 'Hacker News' },
  { value: 'webscraper', label: '网页抓取' },
  { value: 'github', label: 'GitHub' },
];

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-500',
  degraded: 'bg-yellow-500',
  disabled: 'bg-red-500',
};

const STATUS_LABELS: Record<string, string> = {
  active: '正常',
  degraded: '降级',
  disabled: '已禁用',
};

export default function SourcesAdminPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const fetchSources = async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get('/admin/sources');
      setSources(data.sources || []);
    } catch {
      // 静默
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除此数据源吗？')) return;
    try {
      await api.delete(`/admin/sources/${id}`);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch {
      alert('删除失败');
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">数据源管理</h1>
        <div className="flex gap-2">
          <button onClick={fetchSources} className="p-2 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => { setEditingSource(null); setShowAddModal(true); }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium"
          >
            <Plus size={16} /> 添加数据源
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Loader2 size={32} className="animate-spin text-primary-600" /></div>
      ) : sources.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg mb-2">暂无数据源</p>
          <p className="text-sm">点击"添加数据源"开始配置</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((source) => (
            <div key={source.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="p-4 flex items-center gap-4">
                {/* 状态指示器 */}
                <div className={clsx('w-2.5 h-2.5 rounded-full shrink-0', STATUS_COLORS[source.status] || 'bg-gray-400')} title={STATUS_LABELS[source.status]} />

                {/* 信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold truncate">{source.name}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 uppercase">{source.type}</span>
                    {!source.is_enabled && <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400">已停用</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                    <span>间隔: {source.cron_interval} 分钟</span>
                    <span>失败: {source.consecutive_failures} 次</span>
                    {source.last_collected_at && (
                      <span>上次采集: {formatDistanceToNow(new Date(source.last_collected_at), { addSuffix: true, locale: zhCN })}</span>
                    )}
                  </div>
                </div>

                {/* 操作 */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => { setEditingSource(source); setShowAddModal(true); }}
                    className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => setExpandedLogId(expandedLogId === source.id ? null : source.id)}
                    className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1"
                  >
                    日志 {expandedLogId === source.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                  <button
                    onClick={() => handleDelete(source.id)}
                    className="px-3 py-1.5 text-xs rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    删除
                  </button>
                </div>
              </div>

              {/* 采集日志 */}
              {expandedLogId === source.id && <SourceLogViewer sourceId={source.id} />}
            </div>
          ))}
        </div>
      )}

      {/* 添加/编辑弹窗 */}
      {showAddModal && (
        <SourceFormModal
          source={editingSource}
          onClose={() => { setShowAddModal(false); setEditingSource(null); }}
          onSaved={() => { setShowAddModal(false); setEditingSource(null); fetchSources(); }}
        />
      )}
    </div>
  );
}

// ─── 采集日志组件 ───
function SourceLogViewer({ sourceId }: { sourceId: string }) {
  const [logs, setLogs] = useState<CollectionLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get(`/admin/sources/${sourceId}/logs`, { params: { limit: 20 } })
      .then((res) => setLogs(res.data.logs || []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [sourceId]);

  if (isLoading) return <div className="p-4 text-center text-sm text-gray-400">加载日志...</div>;

  return (
    <div className="border-t border-gray-200 dark:border-gray-700">
      {logs.length === 0 ? (
        <div className="p-4 text-center text-sm text-gray-400">暂无采集记录</div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-700 text-gray-500 dark:text-gray-400">
              <th className="text-left px-4 py-2 font-medium">时间</th>
              <th className="text-left px-4 py-2 font-medium">状态</th>
              <th className="text-right px-4 py-2 font-medium">文章数</th>
              <th className="text-left px-4 py-2 font-medium">错误信息</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-gray-50 dark:border-gray-700/50">
                <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                  {new Date(log.started_at).toLocaleString('zh-CN')}
                </td>
                <td className="px-4 py-2">
                  <span className={clsx(
                    'px-1.5 py-0.5 rounded font-medium',
                    log.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                    log.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                    'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                  )}>
                    {log.status === 'success' ? '成功' : log.status === 'failed' ? '失败' : '部分'}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">{log.articles_fetched}</td>
                <td className="px-4 py-2 text-red-500 truncate max-w-[200px]">{log.error_message || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ─── 数据源表单弹窗 ───
function SourceFormModal({
  source,
  onClose,
  onSaved,
}: {
  source: Source | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = !!source;
  const [name, setName] = useState(source?.name || '');
  const [type, setType] = useState(source?.type || 'rss');
  const [interval, setInterval] = useState(String(source?.cron_interval || 30));
  const [isEnabled, setIsEnabled] = useState(source?.is_enabled ?? true);
  const [configJson, setConfigJson] = useState(source ? JSON.stringify(source.config, null, 2) : '{\n  \n}');
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const intervalNum = parseInt(interval);
    if (isNaN(intervalNum) || intervalNum < 15) {
      setError('采集间隔不能低于 15 分钟');
      return;
    }

    let config: Record<string, unknown>;
    try {
      config = JSON.parse(configJson);
    } catch {
      setError('配置 JSON 格式无效');
      return;
    }

    setIsSaving(true);
    try {
      const payload = { name, type, config, cron_interval: intervalNum, is_enabled: isEnabled };
      if (isEdit) {
        await api.patch(`/admin/sources/${source!.id}`, payload);
      } else {
        await api.post('/admin/sources', payload);
      }
      onSaved();
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-lg font-bold mb-4">{isEdit ? '编辑数据源' : '添加数据源'}</h2>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm" />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">类型</label>
              <select value={type} onChange={(e) => setType(e.target.value)} disabled={isEdit}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm disabled:opacity-50">
                {SOURCE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">采集间隔（分钟，最低 15）</label>
              <input type="number" min={15} value={interval} onChange={(e) => setInterval(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm" />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">配置（JSON）</label>
              <textarea value={configJson} onChange={(e) => setConfigJson(e.target.value)} rows={6}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm font-mono" />
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={isEnabled} onChange={(e) => setIsEnabled(e.target.checked)}
                className="rounded border-gray-300" />
              <span className="text-sm">启用</span>
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={onClose}
                className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700">
                取消
              </button>
              <button type="submit" disabled={isSaving}
                className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium disabled:opacity-50">
                {isSaving ? '保存中...' : '保存'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}