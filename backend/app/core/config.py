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

    # 离线 AI（默认开启，优先走本地 Ollama）
    OFFLINE_AI_ENABLED: bool = True
    OFFLINE_AI_PROVIDER: str = "ollama"
    OFFLINE_AI_MODEL: str = "qwen2.5:7b"
    OFFLINE_AI_OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OFFLINE_AI_TIMEOUT_SECONDS: int = 120

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"
    CORS_ALLOW_ORIGIN_REGEX: str | None = (
        r"^https?://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|192\\.168\\.\\d+\\.\\d+|10\\.\\d+\\.\\d+\\.\\d+|172\\.(1[6-9]|2\\d|3[0-1])\\.\\d+\\.\\d+)(:\\d+)?$"
    )
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    @property
    def cors_allow_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOW_ORIGINS.split(",") if item.strip()]

    @property
    def cors_allow_methods(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOW_METHODS.split(",") if item.strip()] or ["*"]

    @property
    def cors_allow_headers(self) -> list[str]:
        return [item.strip() for item in self.CORS_ALLOW_HEADERS.split(",") if item.strip()] or ["*"]

    @property
    def effective_database_url(self) -> str:
        """当配置了 DM_* 字段时优先拼接达梦连接；否则使用 DATABASE_URL。"""
        if self.DM_HOST and self.DM_USER and self.DM_PASSWORD:
            db_part = f"/{self.DM_NAME}" if self.DM_NAME else ""
            return f"dm+dmPython://{self.DM_USER}:{self.DM_PASSWORD}@{self.DM_HOST}:{self.DM_PORT}{db_part}"

        return self.DATABASE_URL or "sqlite:///./aegis.db"


settings = Settings()
