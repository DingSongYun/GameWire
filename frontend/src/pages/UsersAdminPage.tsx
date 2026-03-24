import { useState, useEffect } from 'react';
import { Loader2, Shield, User as UserIcon } from 'lucide-react';
import clsx from 'clsx';
import api from '../services/api';
import type { User, Category } from '../types';

export default function UsersAdminPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <UserManagement />
      <CategoryManagement />
    </div>
  );
}

// ─── 用户管理 ───
function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/users')
      .then((res) => setUsers(res.data.users || res.data || []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const handleRoleChange = async (userId: string, newRole: 'admin' | 'member') => {
    try {
      await api.patch(`/admin/users/${userId}`, { role: newRole });
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
    } catch {
      alert('角色更新失败');
    }
  };

  const handleToggleActive = async (userId: string, isActive: boolean) => {
    try {
      await api.patch(`/admin/users/${userId}`, { is_active: isActive });
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_active: isActive } : u)));
    } catch {
      alert('状态更新失败');
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">用户管理</h1>

      {isLoading ? (
        <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-primary-600" /></div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                <th className="text-left px-4 py-3 font-medium">用户</th>
                <th className="text-left px-4 py-3 font-medium">角色</th>
                <th className="text-left px-4 py-3 font-medium">状态</th>
                <th className="text-right px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-gray-100 dark:border-gray-700/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-bold">
                        {user.display_name?.[0]?.toUpperCase() || '?'}
                      </div>
                      <div>
                        <p className="font-medium">{user.display_name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                      user.role === 'admin'
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                    )}>
                      {user.role === 'admin' ? <Shield size={10} /> : <UserIcon size={10} />}
                      {user.role === 'admin' ? '管理员' : '成员'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      user.is_active
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                    )}>
                      {user.is_active ? '活跃' : '已禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value as 'admin' | 'member')}
                        className="px-2 py-1 rounded border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-xs"
                      >
                        <option value="member">成员</option>
                        <option value="admin">管理员</option>
                      </select>
                      <button
                        onClick={() => handleToggleActive(user.id, !user.is_active)}
                        className={clsx(
                          'px-2.5 py-1 rounded text-xs font-medium',
                          user.is_active
                            ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20'
                            : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                        )}
                      >
                        {user.is_active ? '禁用' : '启用'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 分类管理 ───
function CategoryManagement() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [newNameZh, setNewNameZh] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const fetchCategories = () => {
    api.get('/categories')
      .then((res) => setCategories(res.data.categories || []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  };

  useEffect(() => { fetchCategories(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsAdding(true);
    try {
      await api.post('/admin/categories', {
        name: newName.trim(),
        name_zh: newNameZh.trim() || null,
        slug: newName.trim().toLowerCase().replace(/\s+/g, '-'),
      });
      setNewName('');
      setNewNameZh('');
      fetchCategories();
    } catch {
      alert('添加失败');
    } finally {
      setIsAdding(false);
    }
  };

  const handleToggleActive = async (catId: string, isActive: boolean) => {
    try {
      await api.patch(`/admin/categories/${catId}`, { is_active: isActive });
      setCategories((prev) => prev.map((c) => (c.id === catId ? { ...c, is_active: isActive } : c)));
    } catch {
      alert('更新失败');
    }
  };

  const handleRename = async (catId: string) => {
    const newNameInput = prompt('输入新的分类名称（英文）:');
    if (!newNameInput) return;
    const newNameZhInput = prompt('输入新的中文名称（可选）:') || undefined;
    try {
      await api.patch(`/admin/categories/${catId}`, { name: newNameInput, name_zh: newNameZhInput });
      fetchCategories();
    } catch {
      alert('重命名失败');
    }
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">分类管理</h2>

      {/* 添加分类 */}
      <form onSubmit={handleAdd} className="flex gap-2 mb-4">
        <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
          placeholder="英文名称" required
          className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm flex-1" />
        <input type="text" value={newNameZh} onChange={(e) => setNewNameZh(e.target.value)}
          placeholder="中文名称（可选）"
          className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm flex-1" />
        <button type="submit" disabled={isAdding}
          className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium disabled:opacity-50">
          添加
        </button>
      </form>

      {isLoading ? (
        <div className="flex justify-center py-10"><Loader2 size={24} className="animate-spin text-primary-600" /></div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                <th className="text-left px-4 py-3 font-medium">名称</th>
                <th className="text-left px-4 py-3 font-medium">中文名</th>
                <th className="text-left px-4 py-3 font-medium">状态</th>
                <th className="text-right px-4 py-3 font-medium">文章数</th>
                <th className="text-right px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.id} className="border-b border-gray-100 dark:border-gray-700/50">
                  <td className="px-4 py-3 font-medium">{cat.name}</td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{cat.name_zh || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-0.5 rounded text-xs font-medium',
                      cat.is_active
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    )}>
                      {cat.is_active ? '激活' : '已禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{cat.article_count ?? '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => handleRename(cat.id)}
                        className="px-2.5 py-1 rounded text-xs hover:bg-gray-100 dark:hover:bg-gray-700">
                        重命名
                      </button>
                      <button
                        onClick={() => handleToggleActive(cat.id, !cat.is_active)}
                        className={clsx(
                          'px-2.5 py-1 rounded text-xs font-medium',
                          cat.is_active ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20' : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                        )}
                      >
                        {cat.is_active ? '禁用' : '启用'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}