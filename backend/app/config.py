from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从环境变量加载"""

    # 数据库
    database_url: str = "postgresql+asyncpg://gamewire:gamewire_dev@localhost:5432/gamewire"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-to-a-secure-random-string"
    jwt_access_token_expire_minutes: int = 1440  # 24 小时
    jwt_refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"

    # OpenAI / LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_daily_token_budget: int = 1_000_000

    # Twitter/X
    twitter_bearer_token: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "GameWire/0.1.0"

    # GitHub
    github_token: str = ""

    # 应用
    app_name: str = "GameWire"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    default_admin_email: str = "admin@gamewire.local"
    default_admin_password: str = "change-me-on-first-login"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
