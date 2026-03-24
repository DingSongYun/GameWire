from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.articles import router as articles_router
from app.api.auth import admin_router as auth_admin_router
from app.api.auth import router as auth_router
from app.api.categories import admin_router as categories_admin_router
from app.api.categories import router as categories_router
from app.api.sources import router as sources_router
from app.api.trends import router as trends_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动逻辑
    from app.adapters.registry import discover_adapters
    from app.services.scheduler import start_scheduler, stop_scheduler

    discover_adapters()
    await start_scheduler()
    yield
    # 关闭逻辑
    await stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="游戏行业 & AI 技术资讯聚合平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(auth_admin_router)
app.include_router(sources_router)
app.include_router(articles_router)
app.include_router(categories_router)
app.include_router(categories_admin_router)
app.include_router(trends_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}