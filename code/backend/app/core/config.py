from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import validator

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    APP_NAME: str = "运维助手 Aegis API"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 默认数据库连接（开发环境可直接用 SQLite）
    DATABASE_URL: str = "sqlite:///./aegis.db"

    # MySQL 连接可拆分配置，便于运维按字段注入
    MYSQL_HOST: Optional[str] = None
    MYSQL_PORT: int = 3306
    MYSQL_NAME: Optional[str] = None
    MYSQL_USER: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_CHARSET: str = "utf8mb4"

    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str

    # AI provider routing
    AI_PROVIDER: str = "ollama"
    AI_FALLBACK_PROVIDER: str = "mock"
    OPENCLAW_BASE_URL: Optional[str] = None
    OPENCLAW_API_KEY: Optional[str] = None
    OPENCLAW_TIMEOUT_SECONDS: int = 120
    OPENCLAW_MODEL: str = "openclaw"
    OPENCLAW_RESPONSES_PATH: str = "/v1/responses"
    OPENCLAW_ADAPTER_ENABLED: bool = False
    OPENCLAW_ADAPTER_TOKEN: str = "local-dev-openclaw-token"
    OPENCLAW_CHAT_PATH: str = "/aegis/ai/chat"
    OPENCLAW_DIAGNOSE_PATH: str = "/aegis/ai/diagnose"
    OPENCLAW_LOG_ANALYZE_PATH: str = "/aegis/ai/log-analyze"

    # Internal AI gateway. Use AI_PROVIDER=internal_gateway to route all AI
    # requests through a server-side gateway that can adapt to pi-agent or
    # other provider-specific APIs.
    INTERNAL_AI_GATEWAY_BASE_URL: Optional[str] = None
    INTERNAL_AI_GATEWAY_API_KEY: Optional[str] = None
    INTERNAL_AI_GATEWAY_TIMEOUT_SECONDS: int = 120
    INTERNAL_AI_GATEWAY_PROVIDER: str = "pi-agent"
    INTERNAL_AI_GATEWAY_MODEL: str = "pi-agent"
    INTERNAL_AI_GATEWAY_CHAT_PATH: str = "/v1/chat"
    INTERNAL_AI_GATEWAY_DIAGNOSE_PATH: str = "/v1/diagnose"
    INTERNAL_AI_GATEWAY_LOG_ANALYZE_PATH: str = "/v1/log-analyze"

    # 离线 AI（默认开启，优先走本地 Ollama）
    OFFLINE_AI_ENABLED: bool = True
    OFFLINE_AI_PROVIDER: str = "ollama"
    OFFLINE_AI_MODEL: str = "qwen2.5:7b"
    OFFLINE_AI_OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OFFLINE_AI_TIMEOUT_SECONDS: int = 120

    # ThreatBook
    THREATBOOK_API_KEY: Optional[str] = None
    THREATBOOK_TIMEOUT_SECONDS: int = 30

    # CORS
    CORS_ALLOW_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = (
        r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)(:\d+)?$"
    )
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    @property
    def cors_allow_origins(self) -> List[str]:
        return [item.strip() for item in self.CORS_ALLOW_ORIGINS.split(",") if item.strip()]

    @property
    def cors_allow_methods(self) -> List[str]:
        return [item.strip() for item in self.CORS_ALLOW_METHODS.split(",") if item.strip()] or ["*"]

    @property
    def cors_allow_headers(self) -> List[str]:
        return [item.strip() for item in self.CORS_ALLOW_HEADERS.split(",") if item.strip()] or ["*"]

    @validator("SECRET_KEY", "INIT_ADMIN_PASSWORD")
    @classmethod
    def reject_weak_defaults(cls, value: str) -> str:
        weak_values = {"", "change_me", "admin123", "change_me_to_a_random_secret"}
        if value.strip() in weak_values:
            raise ValueError("安全配置不允许使用弱默认值，请通过环境变量设置强密码/密钥")
        return value

    @property
    def effective_database_url(self) -> str:
        """当配置了 MYSQL_* 字段时优先拼接 MySQL 连接；否则使用 DATABASE_URL。"""
        if self.MYSQL_HOST and self.MYSQL_USER and self.MYSQL_PASSWORD:
            db_name = self.MYSQL_NAME or "aegis"
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{db_name}?charset={self.MYSQL_CHARSET}"
            )

        return self.DATABASE_URL or "sqlite:///./aegis.db"


settings = Settings()
