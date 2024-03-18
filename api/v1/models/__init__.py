"""
API에서 필요한 기본적인 모델을 정의합니다.
TODO: 역할에 따른 재구성 작업이 필요.
"""
from datetime import datetime
from typing_extensions import Annotated

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from core.database import DBConnect
from core.models import Base, DB_TABLE_PREFIX


class MemberRefreshToken(Base):
    """회원 Refresh Token 테이블 모델"""
    __tablename__ = DB_TABLE_PREFIX + "member_refresh_token"

    id = Column(Integer, primary_key=True, index=True)
    mb_id = Column(String(20), index=True, nullable=False, default="") # ForeignKey(DB_TABLE_PREFIX + "member.mb_id")
    refresh_token = Column(String(255), unique=True)
    expires_at = Column(DateTime, default=datetime.now) # Refresh Token의 만료 시간입니다.
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

# MemberRefreshToken 테이블 생성
# TODO: 
#   1. 테이블이 생성되는 시점에 대해 고민이 필요함
#       - 설치할 때 같이 만들것인지
#       - API사용 옵션을 두어서 설정할 때 만들것인지 등등..
#   2. 만료된 Refresh Token을 주기적으로 삭제하는 작업이 필요함
MemberRefreshToken.__table__.create(bind=DBConnect().engine, checkfirst=True)


class Message(BaseModel):
    """메시지 응답 모델 (API Docs)"""
    detail: str

responses_403 = {
    403: {"model": Message}
}
responses = {
    403: {"model": Message},
    409: {"model": Message}
}

class ViewPageModel(BaseModel):
    page: Annotated[int, Query(title="페이지 번호")] = 1
    per_page: Annotated[int, Query(title="페이지 당 쪽지 수")] = 10

class ResponsePageListModel(BaseModel):
    total_records: int
    total_pages: int