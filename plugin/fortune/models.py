from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text

from core.database import DBConnect
from core.models import Base


class Fortune(Base):
    __tablename__ = DBConnect().table_prefix + "fortunes"
    id = Column(Integer, primary_key=True, index=True)
    birth_date = Column(DateTime, index=True)  # 생년월일
    birth_time = Column(String(length=10))     # 태어난 시간
    fortune_info = Column(String(length=200))  # 오늘의 운세 정보
    user_ip = Column(String(length=15))        # 사용자 IP
    created_at = Column(DateTime, default=datetime.now)  # 일시