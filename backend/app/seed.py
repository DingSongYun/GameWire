"""种子数据脚本：插入默认分类和初始管理员用户"""
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.models import Category, User, UserRole

# 默认分类
DEFAULT_CATEGORIES = [
    {"name": "AI Technology", "name_zh": "AI 技术", "slug": "ai-technology", "display_order": 1},
    {"name": "Game Engine", "name_zh": "游戏引擎", "slug": "game-engine", "display_order": 2},
    {"name": "Industry News", "name_zh": "行业新闻", "slug": "industry-news", "display_order": 3},
    {"name": "Market Trends", "name_zh": "市场动态", "slug": "market-trends", "display_order": 4},
    {"name": "Dev Tools", "name_zh": "开发工具", "slug": "dev-tools", "display_order": 5},
    {"name": "Graphics & Rendering", "name_zh": "图形渲染", "slug": "graphics-rendering", "display_order": 6},
    {"name": "Networking", "name_zh": "网络技术", "slug": "networking", "display_order": 7},
    {"name": "Company News", "name_zh": "公司动态", "slug": "company-news", "display_order": 8},
]


async def seed_categories(session: AsyncSession) -> None:
    """插入默认分类（跳过已存在的）"""
    for cat_data in DEFAULT_CATEGORIES:
        existing = await session.execute(
            select(Category).where(Category.slug == cat_data["slug"])
        )
        if existing.scalar_one_or_none() is None:
            category = Category(
                id=uuid.uuid4(),
                name=cat_data["name"],
                name_zh=cat_data["name_zh"],
                slug=cat_data["slug"],
                display_order=cat_data["display_order"],
                is_active=True,
            )
            session.add(category)
            print(f"  ✓ 分类已创建: {cat_data['name_zh']} ({cat_data['name']})")
        else:
            print(f"  - 分类已存在: {cat_data['name_zh']}")


async def seed_admin_user(session: AsyncSession) -> None:
    """创建初始管理员用户（跳过已存在的）"""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    existing = await session.execute(
        select(User).where(User.email == settings.default_admin_email)
    )
    if existing.scalar_one_or_none() is None:
        admin = User(
            id=uuid.uuid4(),
            email=settings.default_admin_email,
            hashed_password=pwd_context.hash(settings.default_admin_password),
            display_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        print(f"  ✓ 管理员用户已创建: {settings.default_admin_email}")
    else:
        print(f"  - 管理员用户已存在: {settings.default_admin_email}")


async def run_seed() -> None:
    """运行所有种子数据"""
    print("🌱 开始插入种子数据...")

    async with async_session() as session:
        print("\n📂 创建默认分类:")
        await seed_categories(session)

        print("\n👤 创建管理员用户:")
        await seed_admin_user(session)

        await session.commit()

    print("\n✅ 种子数据插入完成!")


if __name__ == "__main__":
    asyncio.run(run_seed())
