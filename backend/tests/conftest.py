import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 测试环境覆盖，避免依赖本地 .env 默认值
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
TEST_DB_PATH = Path(__file__).resolve().parent / "test_aegis.db"
os.environ["SECRET_KEY"] = "test_secret_key_for_ci_only_please_change"
os.environ["INIT_ADMIN_PASSWORD"] = "test_admin_password_for_ci_only"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("OFFLINE_AI_ENABLED", "false")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.db.session as db_session_module  # noqa: E402
from app.main import app, init_seed  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture()
def setup_test_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(os.environ["DATABASE_URL"], future=True, connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session_module.engine = engine
    db_session_module.SessionLocal = testing_session_local

    db = testing_session_local()
    try:
        init_seed(db)
    finally:
        db.close()

    yield

    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


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
def admin_headers(admin_token: str) -> dict[str, str]:
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
