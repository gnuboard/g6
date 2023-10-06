import os

from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

from config import load_gnuboard_env

load_gnuboard_env()
DB = {
    'drivername': os.getenv("G6_DB_DRIVER", ""), 
    'host': os.getenv("G6_DB_HOST", ""),
    'port': int(os.getenv("G6_DB_PORT")),
    'username': os.getenv("G6_DB_USER", ""),
    'password': os.getenv("G6_DB_PASSWORD", ""),
    'database': os.getenv("G6_DB_NAME", ""),
    'query': {'charset': os.getenv("G6_DB_CHARSET", "utf8")}
}

engine = create_engine(
    URL(**DB),
    pool_size=20,   # adjust as needed
    max_overflow=40, # adjust as needed
    pool_timeout=60
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
