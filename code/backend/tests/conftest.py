from typing import Any, Dict, List, Optional, Set, Tuple
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 测试环境覆盖，避免依赖本地 .env 默认值
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ["SECRET_KEY"] = "test_secret_key_for_ci_only_please_change"
os.environ["INIT_ADMIN_PASSWORD"] = "test_admin_password_for_ci_only"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("OFFLINE_AI_ENABLED", "false")
os.environ["INTERNAL_AI_GATEWAY_CHAT_PATH"] = "/v1/chat"
os.environ["INTERNAL_AI_GATEWAY_DIAGNOSE_PATH"] = "/v1/diagnose"
os.environ["INTERNAL_AI_GATEWAY_LOG_ANALYZE_PATH"] = "/v1/log-analyze"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db.session as db_session_module  # noqa: E402
import app.main as app_main_module  # noqa: E402
from app.main import app, init_seed  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def setup_test_db():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session_module.engine = engine
    db_session_module.SessionLocal = testing_session_local
    app_main_module.SessionLocal = testing_session_local

    db = testing_session_local()
    try:
        init_seed(db)
    finally:
        db.close()

    yield

    engine.dispose()


@pytest.fixture()
def client(setup_test_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test_admin_password_for_ci_only"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def super_admin_user(setup_test_db):
    db = db_session_module.SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        assert user is not None
        yield user
    finally:
        db.close()
