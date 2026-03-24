# GameWire Backend

## API 文档

启动后端后，访问自动生成的 OpenAPI 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 本地开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest
```

## 目录结构

- `app/adapters/` — 数据源适配器（RSS, Twitter, Reddit, HN, GitHub, WebScraper）
- `app/api/` — API 端点路由（auth, articles, categories, trends, sources）
- `app/models/` — SQLAlchemy 模型（14 张表）
- `app/pipeline/` — AI 处理管线（清洗→去重→语言→摘要→分类→翻译）
- `app/services/` — 业务逻辑（认证、调度、趋势分析、摘要生成）
