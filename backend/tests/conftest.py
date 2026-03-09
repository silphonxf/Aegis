import os

# 测试环境覆盖，避免依赖本地 .env 默认值
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_ci_only_please_change")
os.environ.setdefault("INIT_ADMIN_PASSWORD", "test_admin_password_for_ci_only")
