## ADDED Requirements

### Requirement: 统一数据源适配器接口
系统必须提供一个抽象的 SourceAdapter 接口，所有数据源实现必须遵循该接口。接口必须定义以下方法：内容抓取、数据源健康状态上报、返回统一结构的文章对象（包含字段：title、url、content_snippet、author、published_at、source_name、raw_metadata）。

#### Scenario: 新数据源适配器注册
- **WHEN** 开发者创建一个实现 SourceAdapter 接口的新类
- **THEN** 系统必须自动发现并注册该数据源，无需修改核心管线代码

#### Scenario: 适配器返回标准化输出
- **WHEN** 任何适配器从其数据源抓取内容
- **THEN** 输出必须符合统一的文章 Schema，与底层数据源格式无关

### Requirement: RSS/Atom 订阅源采集
系统必须通过专用的 RSSAdapter 支持 RSS 和 Atom 订阅源的抓取与解析。用户必须能够通过系统配置界面添加自定义 RSS 订阅源 URL。

#### Scenario: 解析标准 RSS 订阅源
- **WHEN** RSSAdapter 抓取一个 RSS 2.0 格式的订阅源 URL
- **THEN** 系统必须提取每条条目的标题、链接、描述、作者和发布日期

#### Scenario: 解析 Atom 订阅源
- **WHEN** RSSAdapter 抓取一个 Atom 格式的订阅源 URL
- **THEN** 系统必须提取每条条目的标题、链接、摘要、作者和更新日期

#### Scenario: 自定义订阅源添加
- **WHEN** 管理员通过配置界面添加一个新的 RSS 订阅源 URL
- **THEN** 系统必须验证该 URL、尝试测试抓取，验证通过后将其注册为定时采集任务

### Requirement: Twitter/X 数据源采集
系统必须通过专用的 TwitterAdapter，使用 Twitter API v2 从 Twitter/X 抓取推文。适配器必须支持基于关键词的搜索和列表/账号监控。

#### Scenario: 关键词搜索采集
- **WHEN** TwitterAdapter 使用配置的关键词（如 "game AI"、"游戏引擎"）执行定时采集
- **THEN** 系统必须抓取上一个采集周期内匹配的推文，并转换为统一的文章 Schema

#### Scenario: API 速率限制处理
- **WHEN** Twitter API 返回速率限制错误（HTTP 429）
- **THEN** 适配器必须暂停该数据源的采集、记录事件日志，并在速率限制重置窗口后重试

### Requirement: Reddit 数据源采集
系统必须通过专用的 RedditAdapter，使用 Reddit API 从指定的子版块抓取帖子。适配器必须支持从配置的子版块（如 r/gamedev、r/MachineLearning、r/artificial）采集内容。

#### Scenario: 子版块内容采集
- **WHEN** RedditAdapter 对 r/gamedev 执行定时采集
- **THEN** 系统必须抓取配置时间窗口内的热门/最新帖子，并转换为统一的文章 Schema，包含帖子标题、正文或链接、作者、得分和评论数

#### Scenario: 速率限制合规
- **WHEN** Reddit API 速率限制即将达到上限
- **THEN** 适配器必须限制请求频率，确保不超出 API 限制

### Requirement: Hacker News 数据源采集
系统必须通过专用的 HackerNewsAdapter，使用 Firebase API 从 Hacker News 抓取文章。

#### Scenario: 热门文章采集
- **WHEN** HackerNewsAdapter 执行定时采集
- **THEN** 系统必须抓取热门文章，并转换为统一的文章 Schema，包含标题、URL、作者、得分和评论数

#### Scenario: 相关性过滤
- **WHEN** 从 Hacker News 抓取到文章
- **THEN** 系统必须应用配置的关键词过滤器，仅保留与游戏行业和 AI 相关的文章

### Requirement: 网页爬取数据源采集
系统必须通过 WebScraperAdapter 支持从配置的游戏行业资讯网站（如 GamesIndustry.biz、GameDev.net、触乐、游研社）爬取内容。

#### Scenario: 结构化页面爬取
- **WHEN** WebScraperAdapter 爬取一个已配置的资讯网站
- **THEN** 系统必须根据站点特定的提取规则，提取文章标题、URL、摘要/节选、作者和发布日期

#### Scenario: Robots.txt 合规
- **WHEN** WebScraperAdapter 初始化目标网站的爬取任务
- **THEN** 系统必须获取并遵守该网站的 robots.txt 指令，跳过被禁止的路径

### Requirement: GitHub Trending 数据源采集
系统必须通过专用的 GitHubAdapter 从 GitHub 抓取热门仓库，聚焦于游戏开发和 AI 相关类别。

#### Scenario: 热门仓库采集
- **WHEN** GitHubAdapter 执行定时采集
- **THEN** 系统必须抓取按相关主题（gamedev、game-engine、machine-learning、artificial-intelligence）筛选的热门仓库，并转换为统一的文章 Schema

### Requirement: 集中式采集调度器
系统必须提供集中式调度器，以独立可配置的时间间隔（cron 表达式）触发每个数据源适配器。每个数据源的最小允许采集间隔必须为 15 分钟，以避免滥用。

#### Scenario: 独立调度
- **WHEN** 调度器配置 RSS 为 30 分钟间隔、Twitter 为 60 分钟间隔
- **THEN** 每个适配器必须按照各自配置的频率独立触发

#### Scenario: 最小间隔强制执行
- **WHEN** 管理员尝试将采集间隔设置为低于 15 分钟
- **THEN** 系统必须拒绝该配置，并返回指明最小允许间隔的错误信息

#### Scenario: 采集失败重试
- **WHEN** 数据源适配器未能完成一次采集（网络错误、API 错误）
- **THEN** 调度器必须以指数退避策略重试最多 3 次，然后将该数据源标记为降级状态，继续执行下一次计划采集

### Requirement: 数据源健康监控
系统必须跟踪每个已配置数据源的健康状态，包括最后成功采集时间、连续失败次数和当前状态（active/degraded/disabled）。

#### Scenario: 数据源降级检测
- **WHEN** 数据源适配器连续 5 次采集失败
- **THEN** 系统必须将该数据源标记为"降级"状态，并在管理员仪表板上发出可见警告

#### Scenario: 数据源健康仪表板
- **WHEN** 管理员查看数据源管理页面
- **THEN** 系统必须显示每个数据源的状态、最后采集时间、上次运行的文章数量和错误历史