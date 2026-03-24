# GameWire Frontend

## 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器（自动代理 API 到 localhost:8000）
npm run dev

# 构建生产版本
npm run build

# 运行测试
npm test
```

## 组件结构

### 页面 (`src/pages/`)
| 文件 | 路由 | 说明 |
|------|------|------|
| `FeedPage.tsx` | `/` | 文章信息流（无限滚动 + 筛选） |
| `TrendsPage.tsx` | `/trends` | 趋势仪表板（图表 + 标签云） |
| `BookmarksPage.tsx` | `/bookmarks` | 收藏列表 |
| `LoginPage.tsx` | `/login` | 登录页 |
| `RegisterPage.tsx` | `/register` | 注册页 |
| `SourcesAdminPage.tsx` | `/admin/sources` | 数据源管理（仅管理员） |
| `UsersAdminPage.tsx` | `/admin/users` | 用户+分类管理（仅管理员） |

### 核心组件 (`src/components/`)
- `AppShell.tsx` — 响应式布局（侧边栏 + 底部导航 + 搜索栏）
- `ArticleCard.tsx` — 文章卡片
- `ArticleDetailModal.tsx` — 文章详情弹窗
- `FilterBar.tsx` — 筛选栏（URL 持久化）
- `CommentSection.tsx` — 评论区
- `TrendLineChart.tsx` — Recharts 折线图
- `TrendComparisonChart.tsx` — 多线对比图
- `CategoryDistributionChart.tsx` — 环形图
- `TagCloud.tsx` — 加权标签云
- `WeeklyDigest.tsx` — 每周摘要展示
- `ProtectedRoute.tsx` — 路由守卫

### Hooks (`src/hooks/`)
- `useAuth.tsx` — 认证上下文（登录/登出/令牌管理）
- `useDarkMode.ts` — 暗色模式（系统偏好 + 手动切换）

### 服务 (`src/services/`)
- `api.ts` — Axios 客户端（JWT 拦截器 + 自动刷新令牌）
