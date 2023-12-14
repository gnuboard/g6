from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

from common.database import DB_TABLE_PREFIX

Base = declarative_base()


class Todo(Base):
    __tablename__ = DB_TABLE_PREFIX + "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(length=50), index=True)
    content = Column(Text(length=255))
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
