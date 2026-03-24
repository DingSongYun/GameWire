# 🎮 GameWire — 游戏行业资讯聚合平台

> 面向游戏公司技术团队的 AI 驱动资讯聚合、分类与趋势分析工具

## ✨ 功能概览

- **多源聚合**: 支持 RSS、Twitter/X、Reddit、Hacker News、GitHub、通用网页抓取 6 种数据源
- **AI 处理管线**: 自动清洗 → 去重 → 语言检测 → AI 摘要 → 智能分类 → 中英翻译
- **趋势分析**: 每日频率聚合、上升话题检测、多维度对比、分类分布、每周 AI 摘要
- **团队协作**: 收藏、评论、已读标记、可分享的筛选视图
- **现代 UI**: 响应式设计、暗色模式、无限滚动、标签云、趋势图表

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│   TypeScript · Vite · Tailwind CSS · Recharts        │
├─────────────────────────────────────────────────────┤
│                    Backend (FastAPI)                  │
│   Python 3.11+ · SQLAlchemy (Async) · LangChain      │
├──────────────┬──────────────┬────────────────────────┤
│  PostgreSQL  │    Redis     │    OpenAI GPT-4o-mini  │
│  (数据存储)   │  (缓存/预算)  │    (AI 摘要/分类)       │
└──────────────┴──────────────┴────────────────────────┘
```

## 🚀 快速开始

### 前提条件

- Docker & Docker Compose
- (可选) Python 3.11+, Node.js 18+

### 1. 克隆项目

```bash
git clone <repo-url>
cd GameWire
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 3. 启动所有服务

```bash
docker compose up -d
```

服务启动后：
- 🌐 前端: http://localhost:5173
- 🔌 后端 API: http://localhost:8000
- 📚 API 文档: http://localhost:8000/docs

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker compose exec backend alembic upgrade head

# 插入种子数据（默认分类 + 管理员账户）
docker compose exec backend python -m app.scripts.seed
```

默认管理员: `admin@gamewire.dev` / `admin123`

## 📁 项目结构

```
GameWire/
├── backend/                 # Python/FastAPI 后端
│   ├── app/
│   │   ├── adapters/        # 数据源适配器 (RSS, Twitter, Reddit, etc.)
│   │   ├── api/             # REST API 端点
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── pipeline/        # AI 处理管线
│   │   ├── services/        # 业务逻辑 (认证, 调度, 趋势)
│   │   ├── config.py        # 应用配置
│   │   ├── database.py      # 数据库连接
│   │   └── main.py          # FastAPI 入口
│   ├── tests/               # 后端测试
│   ├── alembic/             # 数据库迁移
│   └── pyproject.toml       # Python 依赖
├── frontend/                # React/TypeScript 前端
│   ├── src/
│   │   ├── components/      # UI 组件
│   │   ├── pages/           # 页面
│   │   ├── hooks/           # React Hooks
│   │   ├── services/        # API 客户端
│   │   └── types/           # TypeScript 类型
│   └── package.json         # 前端依赖
├── docker-compose.yml       # Docker 编排
└── .env.example             # 环境变量模板
```

## 🔑 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接 | `postgresql+asyncpg://user:pass@localhost:5432/gamewire` |
| `REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |
| `JWT_SECRET` | JWT 签名密钥 | 随机 32 位字符串 |
| `CORS_ORIGINS` | 前端域名 | `http://localhost:5173` |

## 📊 API 端点概览

### 认证 (6 个)
- `POST /api/auth/register` — 注册
- `POST /api/auth/login` — 登录
- `POST /api/auth/refresh` — 刷新令牌
- `GET /api/auth/me` — 当前用户

### 文章 (11 个)
- `GET /api/articles` — 分页列表 (筛选+排序)
- `GET /api/articles/search` — 全文搜索
- `GET /api/articles/{id}` — 文章详情
- `POST /api/articles/{id}/bookmark` — 收藏
- `POST /api/articles/{id}/comments` — 评论
- `POST /api/articles/{id}/translate` — 按需翻译

### 趋势 (6 个)
- `GET /api/trends/topics` — 趋势话题
- `GET /api/trends/topic/{tag_id}/timeseries` — 时间序列
- `GET /api/trends/compare` — 多话题对比
- `GET /api/trends/distribution` — 分类分布
- `GET /api/trends/digests` — 每周摘要列表
- `GET /api/trends/digests/latest` — 最新摘要

### 管理 (仅管理员)
- `GET/POST/PATCH/DELETE /api/admin/sources` — 数据源管理
- `GET/PATCH /api/admin/users` — 用户管理
- `POST/PATCH /api/admin/categories` — 分类管理

## 🧪 测试

```bash
# 后端测试
cd backend && pytest

# 前端测试
cd frontend && npm test
```

## 📄 License

MIT
