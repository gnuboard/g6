from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

load_dotenv()
DB_ENGINE = os.getenv("DB_ENGINE").lower()  # 소문자
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_TABLE_PREFIX = os.getenv("DB_TABLE_PREFIX")

if DB_ENGINE == "mysql":
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_ENGINE == "postgresql":
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"sqlite:///sqlite3.db"


engine = create_engine(
    DATABASE_URL,
    # convert_unicode=True, 
    poolclass=QueuePool,
    pool_size=20,  # adjust as needed
    max_overflow=40,  # adjust as needed
    pool_timeout=60,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
