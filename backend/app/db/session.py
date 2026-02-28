from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

db_url = settings.effective_database_url
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(SessionLocal, "before_flush")
def _assign_pk_for_dm(session, flush_context, instances):
    # DM current schema may use plain INTEGER PK without identity; assign id in app layer as fallback.
    if not db_url.startswith("dm+"):
        return

    for obj in list(session.new):
        if not hasattr(obj, "id") or getattr(obj, "id", None) is not None:
            continue
        table = getattr(obj, "__table__", None)
        if table is None or "id" not in table.c:
            continue
        next_id = session.execute(select(func.coalesce(func.max(table.c.id), 0) + 1)).scalar_one()
        setattr(obj, "id", int(next_id))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
