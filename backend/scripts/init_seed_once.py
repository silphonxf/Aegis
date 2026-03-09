#!/usr/bin/env python3
"""显式初始化基础角色、管理员与示例系统（仅首装执行一次）。"""

from app.db.session import SessionLocal
from app.main import init_seed


def main() -> None:
    db = SessionLocal()
    try:
        init_seed(db)
        print("✅ 初始化完成：roles/admin/demo-system")
    finally:
        db.close()


if __name__ == "__main__":
    main()
