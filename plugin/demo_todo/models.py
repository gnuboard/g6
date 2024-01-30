from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from core.database import DBConnect
from core.models import Base


class Todo(Base):
    __tablename__ = DBConnect().table_prefix + "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(length=50), index=True)
    content = Column(Text)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


# 상단의 (Base) 를 상속받은 모델들을 DB 에 테이블 생성한다. 최하단에 있어야한다.
Base.metadata.create_all(bind=DBConnect().engine)
