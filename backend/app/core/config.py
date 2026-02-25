from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "运维助手 Aegis API"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    DM_DSN: str = "dm+dmPython://SYSDBA:SYSDBA@127.0.0.1:5236/MAIN"


settings = Settings()
