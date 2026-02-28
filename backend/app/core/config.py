from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "运维助手 Aegis API"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 默认数据库连接（开发环境可直接用 SQLite）
    DATABASE_URL: str = "sqlite:///./aegis.db"

    # 达梦连接可拆分配置，便于运维按字段注入
    DM_HOST: str | None = None
    DM_PORT: int = 5236
    DM_NAME: str | None = None
    DM_USER: str | None = None
    DM_PASSWORD: str | None = None

    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "admin123"

    @property
    def effective_database_url(self) -> str:
        """当配置了 DM_* 字段时优先拼接达梦连接；否则使用 DATABASE_URL。"""
        if self.DM_HOST and self.DM_USER and self.DM_PASSWORD:
            db_part = f"/{self.DM_NAME}" if self.DM_NAME else ""
            return f"dm+dmPython://{self.DM_USER}:{self.DM_PASSWORD}@{self.DM_HOST}:{self.DM_PORT}{db_part}"

        return self.DATABASE_URL or "sqlite:///./aegis.db"


settings = Settings()
