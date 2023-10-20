from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

load_dotenv()
DB_CASE = os.getenv("DB_CASE")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

if DB_CASE == "mysql":
    DATABASE_URL = f"mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_CASE == "postgresql":
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"sqlite:///sqlite3.db"
    
engine = create_engine(
    DATABASE_URL, 
    # convert_unicode=True, 
    poolclass=QueuePool,
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
