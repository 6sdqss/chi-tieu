from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True, 
    pool_size=10, 
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    import app.models  # Import models để SQLAlchemy nhận diện
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    """Hỗ trợ tự động đóng kết nối DB khi xong việc"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
