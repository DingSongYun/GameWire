## Why

游戏公司技术团队需要持续追踪两个快速演变的领域：AI 技术在游戏中的工程落地，以及游戏行业动态。目前信息分散在数十个网站、社交平台和社区中，技术负责人和团队成员需要花费大量时间手动浏览、筛选和整理。缺少一个统一的工具来聚合、分类和分析这些资讯，导致关键信息遗漏和决策延迟。

## What Changes

- 新建一个资讯聚合平台（项目代号 **GameWire**），从多渠道抓取游戏行业和 AI 技术资讯
- 支持的信息来源：
  - 游戏资讯网站（GamesIndustry.biz、GameDev.net、Gamasutra/Game Developer、IGN、触乐、游研社等）
  - 社交平台（Twitter/X、Reddit 的 r/gamedev、r/MachineLearning、r/artificial 等子版块）
  - 技术社区（Hacker News、GitHub Trending、arXiv AI 相关论文）
  - RSS 订阅源（用户可自定义添加）
- 提供 Web 端界面用于浏览、搜索和团队共享，架构设计需考虑未来集成到桌面终端应用
- 内容自动分类（AI 技术、游戏引擎、行业新闻、市场动态等）
- 趋势分析功能，识别热门话题和技术方向
- 团队共享功能，支持多用户访问和协作

## Capabilities

### New Capabilities

- `content-sourcing`: 多渠道内容采集引擎，支持 RSS、网页爬取、Twitter API、Reddit API 等数据源的统一接入和调度
- `content-processing`: 内容处理管线，包括去重、清洗、AI 自动摘要、语言检测与翻译（中英双语支持）
- `content-classification`: 内容智能分类与标签系统，基于预定义类别（AI 技术、游戏引擎、行业新闻、市场动态等）自动归类
- `trend-analysis`: 趋势分析引擎，基于时间维度的话题热度追踪、关键词频率分析、技术方向洞察
- `web-dashboard`: Web 端仪表板，提供资讯浏览、搜索、筛选、趋势可视化等功能，响应式设计
- `team-sharing`: 团队协作功能，支持多用户访问、内容收藏、评论标注、分享链接

### Modified Capabilities

（无 —— 这是全新项目，暂无已有能力需要修改）

## Impact

- **新代码库**: 从零构建，包括后端服务（API + 采集调度）、前端 Web 应用、数据存储层
- **外部 API 依赖**: Twitter/X API、Reddit API、可能的 RSS 解析服务、AI/LLM API（用于摘要和分类）
- **基础设施**: 需要数据库（存储文章和元数据）、定时任务调度器（采集频率管理）、可选的消息队列
- **安全与合规**: API Key 管理、爬虫 robots.txt 遵守、内容版权注意事项
- **可扩展性**: 架构需要预留桌面终端集成接口（未来可通过 API 对接 Electron/Tauri 等桌面框架）
- **团队使用**: 需要用户认证和权限管理基础设施
