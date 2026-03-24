## 1. 项目初始化与基础设施

- [x] 1.1 初始化 Monorepo 目录结构：`backend/`（Python/FastAPI）和 `frontend/`（React/TypeScript/Vite）
- [x] 1.2 创建 `backend/pyproject.toml`，配置依赖：fastapi、uvicorn、sqlalchemy、alembic、asyncpg、redis、pydantic、python-jose（JWT）、passlib、httpx
- [x] 1.3 创建 `frontend/package.json`，配置依赖：react、react-dom、typescript、vite、react-router-dom、axios、recharts、tailwindcss
- [x] 1.4 创建 `docker-compose.yml`，配置服务：postgres（5432）、redis（6379）、backend（8000）、frontend（5173）
- [x] 1.5 创建 `backend/Dockerfile` 和 `frontend/Dockerfile`，用于容器化开发环境
- [x] 1.6 创建 `.env.example`，列出所有必需的环境变量（DATABASE_URL、REDIS_URL、OPENAI_API_KEY、JWT_SECRET 等）
- [x] 1.7 搭建后端项目结构：`backend/app/` 下创建 `main.py`、`config.py`、`database.py`、`models/`、`schemas/`、`api/`、`services/`、`pipeline/`、`adapters/`
- [x] 1.8 搭建前端项目结构：`frontend/src/` 下创建 `components/`、`pages/`、`hooks/`、`services/`、`types/`、`utils/`

## 2. 数据库模型与迁移

- [x] 2.1 在 `backend/app/models/base.py` 中创建 SQLAlchemy 基础模型，包含公共字段（id、created_at、updated_at）
- [x] 2.2 创建 `Source` 模型：id、name、type（枚举：rss/twitter/reddit/hackernews/webscraper/github）、config（JSONB）、cron_interval、is_enabled、status（active/degraded/disabled）、last_collected_at、consecutive_failures
- [x] 2.3 创建 `Article` 模型：id、url（唯一）、title、content_snippet、clean_content、summary、summary_zh（备选翻译）、language、source_id（外键）、author、published_at、simhash_fingerprint、processing_status（枚举）、raw_metadata（JSONB）
- [x] 2.4 创建 `Category` 模型：id、name、name_zh、slug、is_active、display_order
- [x] 2.5 创建 `Tag` 模型：id、canonical_name、aliases（JSONB 数组）
- [x] 2.6 创建 `ArticleCategory` 关联表：article_id、category_id、confidence_score
- [x] 2.7 创建 `ArticleTag` 关联表：article_id、tag_id
- [x] 2.8 创建 `User` 模型：id、email（唯一）、hashed_password、display_name、role（枚举：admin/member）、is_active、last_active_at
- [x] 2.9 创建 `Bookmark` 模型：id、user_id（外键）、article_id（外键）、created_at
- [x] 2.10 创建 `Comment` 模型：id、user_id（外键）、article_id（外键）、content、created_at
- [x] 2.11 创建 `ReadStatus` 模型：user_id、article_id、read_at（复合主键）
- [x] 2.12 创建 `TagFrequency` 模型：id、tag_id（外键）、category_id（外键，可空）、date、count — 用于趋势聚合
- [x] 2.13 创建 `TrendDigest` 模型：id、week_start、content、generated_at
- [x] 2.14 创建 `CollectionLog` 模型：id、source_id（外键）、started_at、completed_at、articles_fetched、status、error_message
- [x] 2.15 初始化 Alembic 并为所有模型创建初始迁移
- [x] 2.16 创建种子数据脚本：插入默认分类（AI 技术、游戏引擎、行业新闻、市场动态、开发工具、图形渲染、网络技术、公司动态）和初始管理员用户
- [x] 2.17 在 Article 的 title 和 summary 列上设置 PostgreSQL 全文搜索索引（tsvector）

## 3. 认证与用户管理

- [x] 3.1 在 `backend/app/services/auth.py` 中使用 passlib（bcrypt）实现密码哈希工具
- [x] 3.2 实现 JWT 令牌的创建和验证（访问令牌 + 刷新令牌），支持可配置的过期时间
- [x] 3.3 创建 FastAPI 依赖项 `get_current_user`，从请求头中的 JWT 提取当前用户
- [x] 3.4 创建 FastAPI 依赖项 `require_admin`，用于保护仅管理员可访问的端点
- [x] 3.5 创建 `POST /api/auth/register` 端点：邮箱 + 密码 → 创建用户（member 角色）→ 返回令牌
- [x] 3.6 创建 `POST /api/auth/login` 端点：邮箱 + 密码 → 验证 → 返回令牌
- [x] 3.7 创建 `POST /api/auth/refresh` 端点：刷新令牌 → 新访问令牌
- [x] 3.8 创建 `GET /api/auth/me` 端点：返回当前用户信息
- [x] 3.9 创建 `GET /api/admin/users` 端点（仅管理员）：列出所有用户及角色和活动信息
- [x] 3.10 创建 `PATCH /api/admin/users/{id}` 端点（仅管理员）：更新用户角色或禁用账号

## 4. 内容采集 — 适配器框架

- [x] 4.1 在 `backend/app/adapters/base.py` 中定义 `SourceAdapter` 抽象基类，包含方法：`fetch()`、`health_check()`，以及统一文章模型（Pydantic 模型：`RawArticle`）
- [x] 4.2 实现适配器自动发现机制：扫描 `backend/app/adapters/` 中的 SourceAdapter 子类，按数据源类型注册
- [x] 4.3 在 `backend/app/adapters/rss_adapter.py` 中实现 `RSSAdapter`，使用 feedparser 解析 RSS 2.0 和 Atom 订阅源
- [x] 4.4 在 `backend/app/adapters/twitter_adapter.py` 中实现 `TwitterAdapter`，使用 httpx 调用 Twitter API v2 进行关键词搜索，包含速率限制处理（HTTP 429 退避）
- [x] 4.5 在 `backend/app/adapters/reddit_adapter.py` 中实现 `RedditAdapter`，使用 httpx（Reddit OAuth2 API）抓取配置子版块的热门/最新帖子
- [x] 4.6 在 `backend/app/adapters/hackernews_adapter.py` 中实现 `HackerNewsAdapter`，使用 HN Firebase API 抓取热门文章，包含关键词相关性过滤
- [x] 4.7 在 `backend/app/adapters/webscraper_adapter.py` 中实现 `WebScraperAdapter`，使用 BeautifulSoup + httpx，支持每个网站可配置的 CSS 选择器，遵守 robots.txt
- [x] 4.8 在 `backend/app/adapters/github_adapter.py` 中实现 `GitHubAdapter`，使用 GitHub REST API 抓取游戏开发/AI 主题的热门仓库
- [x] 4.9 创建数据源管理 API：`GET/POST/PATCH/DELETE /api/admin/sources`（仅管理员），按数据源类型验证配置
- [x] 4.10 创建 `GET /api/admin/sources/{id}/logs` 端点：返回指定数据源的采集历史

## 5. 内容采集 — 调度器

- [x] 5.1 在 `backend/app/services/scheduler.py` 中使用 APScheduler 实现集中式调度器 — 从数据库加载数据源配置，独立调度每个数据源
- [x] 5.2 在数据源配置验证中实现最小间隔强制执行（15 分钟）
- [x] 5.3 实现重试逻辑：每次采集失败后以指数退避策略重试最多 3 次
- [x] 5.4 实现数据源健康追踪：错误时递增 consecutive_failures，成功时重置，连续 5 次失败后标记为"降级"
- [x] 5.5 实现采集日志记录：为每次运行写入 CollectionLog 条目（开始时间、结束时间、数量、状态、错误信息）
- [x] 5.6 在 FastAPI 生命周期钩子中创建调度器启动逻辑：应用启动时初始化并启动调度器

## 6. 内容处理管线

- [x] 6.1 在 `backend/app/pipeline/cleaning.py` 中实现内容清洗模块：剥离 HTML 标签（保留文本结构）、移除 URL 追踪参数、规范化空白字符
- [x] 6.2 在 `backend/app/pipeline/dedup.py` 中实现 URL 去重：检查文章 URL 是否已存在于数据库
- [x] 6.3 在 `backend/app/pipeline/dedup.py` 中实现 SimHash 指纹计算：计算内容的 SimHash，比较汉明距离（阈值：3 位），支持可配置阈值
- [x] 6.4 在 `backend/app/pipeline/language.py` 中实现语言检测：使用轻量级库（如 langdetect 或 lingua）检测文章语言（zh/en）
- [x] 6.5 在 `backend/app/pipeline/summarize.py` 中实现 AI 摘要生成：LangChain + OpenAI GPT-4o-mini 提示词生成 100-200 字摘要，失败时回退到截断摘录
- [x] 6.6 在 `backend/app/pipeline/summarize.py` 中实现每日 Token 预算追踪：在 Redis 中统计 token 使用量，超出预算时停止摘要生成
- [x] 6.7 在 `backend/app/pipeline/classify.py` 中实现 AI 分类：LangChain 提示词分配分类（带置信度分数）并从文章内容提取标签
- [x] 6.8 在 `backend/app/pipeline/classify.py` 中实现标签归一化：将提取的标签与现有规范标签匹配，创建新标签或添加别名
- [x] 6.9 在 `backend/app/pipeline/translate.py` 中实现 AI 翻译：使用 LLM 在中英文之间翻译摘要，缓存结果
- [x] 6.10 在 `backend/app/pipeline/orchestrator.py` 中实现管线编排器：顺序执行（清洗 → 去重 → 语言检测 → 摘要 → 分类 → 翻译），按文章追踪每个阶段状态，支持阶段级重试
- [x] 6.11 将管线与调度器集成：每次数据源采集完成后，将原始文章送入管线编排器处理

## 7. 文章 API

- [x] 7.1 创建 `GET /api/articles` 端点：分页列表（每页 20 篇），按时间倒序，包含分类、标签、数据源信息、当前用户的收藏/阅读状态
- [x] 7.2 添加筛选查询参数：category_ids、tag_ids、source_ids、language、date_from、date_to
- [x] 7.3 创建 `GET /api/articles/{id}` 端点：完整文章详情，包含摘要、分类、标签、评论、收藏状态
- [x] 7.4 创建 `GET /api/articles/search` 端点：使用 PostgreSQL tsvector 全文搜索，支持相关性排序和日期排序
- [x] 7.5 创建 `POST /api/articles/{id}/bookmark` 和 `DELETE /api/articles/{id}/bookmark` 端点
- [x] 7.6 创建 `GET /api/me/bookmarks` 端点：列出用户已收藏的文章
- [x] 7.7 创建 `POST /api/articles/{id}/comments` 端点：添加评论（需认证）
- [x] 7.8 创建 `GET /api/articles/{id}/comments` 端点：列出文章的所有评论
- [x] 7.9 创建 `POST /api/articles/{id}/read` 端点：标记文章为当前用户已读
- [x] 7.10 创建 `GET /api/me/unread-count` 端点：返回当前用户的未读文章数量
- [x] 7.11 创建 `POST /api/articles/{id}/translate` 端点：触发按需翻译，返回翻译后的摘要

## 8. 分类与标签 API

- [x] 8.1 创建 `GET /api/categories` 端点：列出所有激活的分类及文章数量
- [x] 8.2 创建 `POST /api/admin/categories` 端点（仅管理员）：添加新分类
- [x] 8.3 创建 `PATCH /api/admin/categories/{id}` 端点（仅管理员）：重命名或禁用分类
- [x] 8.4 创建 `GET /api/tags` 端点：按频率排序列出标签，支持可选的时间段筛选
- [x] 8.5 创建 `GET /api/tags/cloud` 端点：返回前 N 个标签及频率权重，用于标签云渲染

## 9. 趋势分析引擎

- [x] 9.1 在 `backend/app/services/trends.py` 中实现每日频率聚合任务：按天统计每个标签和每个分类的文章数，存入 TagFrequency 表
- [x] 9.2 实现上升趋势检测：比较当前周期与上一周期的频率，标记增长超过可配置阈值（默认：50%）的话题
- [x] 9.3 创建 `GET /api/trends/topics` 端点：返回前 20 个趋势话题，包含增长率、当前数量、上期数量
- [x] 9.4 创建 `GET /api/trends/topic/{tag_id}/timeseries` 端点：返回指定标签在所选时间范围（7天/30天/90天）内的每日文章数量
- [x] 9.5 创建 `GET /api/trends/compare` 端点：返回 2-5 个标签的叠加时间序列用于对比
- [x] 9.6 创建 `GET /api/trends/distribution` 端点：返回指定时间段内的分类分布（文章数量/百分比）
- [x] 9.7 在 `backend/app/services/digest.py` 中实现每周摘要生成：使用 LLM 生成本周趋势总结、每分类热门文章、显著变化 — 存入 TrendDigest
- [x] 9.8 通过 APScheduler 调度每周摘要生成任务（默认：周一 9:00）
- [x] 9.9 创建 `GET /api/trends/digests` 端点：列出每周摘要
- [x] 9.10 创建 `GET /api/trends/digests/latest` 端点：返回最新摘要，包含未读时的"新"标识

## 10. 前端 — 核心布局与路由

- [x] 10.1 初始化 Vite + React + TypeScript 项目，配置 Tailwind CSS
- [x] 10.2 使用 React Router 设置路由：`/`（信息流）、`/trends`（趋势）、`/bookmarks`（收藏）、`/admin/sources`（数据源管理）、`/admin/users`（用户管理）、`/login`（登录）、`/register`（注册）
- [x] 10.3 创建响应式外壳布局组件：侧边栏导航（桌面端）/ 底部导航（移动端）、主内容区域、顶部搜索栏和用户菜单
- [x] 10.4 实现暗色模式支持：通过 `prefers-color-scheme` 检测系统偏好、手动切换开关、在 localStorage 中持久化偏好
- [x] 10.5 创建 Axios API 客户端，带 JWT 拦截器（自动附加令牌、处理 401 → 刷新令牌流程）
- [x] 10.6 创建认证上下文提供者：登录/登出状态、用户角色、令牌管理

## 11. 前端 — 认证页面

- [x] 11.1 创建登录页面：邮箱/密码表单、错误处理、成功后重定向到信息流
- [x] 11.2 创建注册页面：邮箱/密码/显示名称表单、输入验证、成功后自动登录
- [x] 11.3 实现受保护路由包装器：未认证用户重定向到登录页、管理员专属路由守卫

## 12. 前端 — 文章信息流与详情

- [x] 12.1 创建 ArticleCard 组件：标题、来源徽章、日期、摘要预览、分类彩色标签、标签、收藏图标、评论数量、未读指示器
- [x] 12.2 创建 ArticleFeed 页面：无限滚动文章卡片列表、加载状态、空状态
- [x] 12.3 创建 FilterBar 组件：分类多选、数据源选择、日期范围选择器、语言切换、排序切换（最新/最相关）
- [x] 12.4 在 URL 查询参数中实现筛选条件持久化，支持可分享的筛选视图
- [x] 12.5 创建 SearchBar 组件：全文搜索输入框，带防抖功能，与 FilterBar 集成
- [x] 12.6 创建文章详情展开视图/弹窗：完整摘要、"查看原文"按钮（在新标签页打开源 URL）、翻译按钮、评论区域
- [x] 12.7 创建 CommentSection 组件：评论列表、添加评论表单
- [x] 12.8 创建收藏页面：使用 ArticleCard 组件展示用户已收藏的文章

## 13. 前端 — 趋势仪表板

- [x] 13.1 创建 TrendsPage 布局：趋势话题列表、主图表区域、分类分布
- [x] 13.2 创建 TrendingTopicsList 组件：前 20 个话题，带增长徽章（↑ 百分比），点击可筛选信息流
- [x] 13.3 使用 Recharts 创建 TrendLineChart 组件：单话题时间序列（7天/30天/90天切换）
- [x] 13.4 使用 Recharts 创建 TrendComparisonChart 组件：2-5 个话题叠加，使用不同颜色
- [x] 13.5 使用 Recharts 创建 CategoryDistributionChart 组件：饼图/环形图显示分类百分比
- [x] 13.6 创建 TagCloud 组件：加权标签展示，点击可筛选信息流
- [x] 13.7 创建 WeeklyDigest 组件：展示最新每周摘要内容，带"新"徽章标识

## 14. 前端 — 管理页面

- [x] 14.1 创建数据源管理页面：列出数据源及状态指示器（绿/黄/红）、最后采集时间、文章数量
- [x] 14.2 创建添加数据源表单/弹窗：数据源类型选择、配置字段（按类型动态显示）、间隔输入（最低 15 分钟验证）
- [x] 14.3 创建编辑数据源表单/弹窗：更新配置和间隔、测试连接按钮
- [x] 14.4 创建 SourceLogViewer 组件：按数据源分页展示采集日志表
- [x] 14.5 创建用户管理页面（仅管理员）：用户列表带角色徽章、角色变更下拉框、禁用开关
- [x] 14.6 创建分类管理板块：分类列表、添加/重命名/禁用控件

## 15. 测试

- [x] 15.1 为每个 SourceAdapter 编写单元测试（模拟外部 API）：验证输出符合 RawArticle Schema
- [x] 15.2 为管线各阶段编写单元测试：清洗、去重（URL + SimHash）、语言检测、摘要生成（模拟 LLM）
- [x] 15.3 为分类和标签归一化编写单元测试（模拟 LLM）
- [x] 15.4 为趋势计算编写单元测试：频率聚合、增长检测
- [x] 15.5 为认证流程编写集成测试：注册 → 登录 → 访问受保护端点 → 刷新令牌
- [x] 15.6 为文章 CRUD + 搜索编写集成测试：通过管线创建文章 → 通过 API 查询 → 验证筛选和搜索
- [x] 15.7 使用 React Testing Library 为 ArticleCard、FilterBar、TrendLineChart 编写前端组件测试

## 16. 文档与部署

- [x] 16.1 创建 `README.md`：项目概述、架构图、环境搭建指南、环境变量参考
- [x] 16.2 创建 `backend/README.md`：API 文档参考（由 FastAPI 自动生成的 OpenAPI 文档，路径 `/docs`）
- [x] 16.3 创建 `frontend/README.md`：组件结构和开发指南
- [x] 16.4 配置 Docker Compose 一键启动本地开发环境：`docker compose up` 启动所有服务，支持热更新
- [x] 16.5 创建数据库备份/恢复脚本，用于生产部署
- [x] 16.6 创建 `.github/workflows/ci.yml` 或等效 CI 管线：代码检查、测试、构建验证
