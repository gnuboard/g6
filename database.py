from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

mysql_host = "localhost"
mysql_port = 3306
mysql_user = "root"
mysql_password = "ahffk"
mysql_db = "gnu6"

DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"  # pymysql을 사용합니다.
engine = create_engine(
    DATABASE_URL, 
    convert_unicode=True, 
    pool_size=10,   # adjust as needed
    max_overflow=20 # adjust as needed)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
