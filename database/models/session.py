from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.get('database.url')

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.get('database.pool_size', 5),
    max_overflow=settings.get('database.max_overflow', 10),
    pool_timeout=settings.get('database.timeout', 30),
    pool_recycle=settings.get('database.recycle', 3600),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

