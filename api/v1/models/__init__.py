"""
API에서 필요한 기본적인 모델을 정의합니다.
TODO: 역할에 따른 재구성 작업이 필요.
"""
from datetime import datetime
from enum import Enum

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


class Tags(Enum):
    """API 태그를 정의합니다."""
    AUTH = "인증"
    BOARD = "게시판"
    GROUP = "게시판그룹"
    CONFIG = "환경설정"
    CONTENT = "컨텐츠"
    FAQ = "FAQ"
    MEMBER = "회원"
    MEMO = "쪽지"
    MENU = "메뉴"
    NEWWIN = "레이어 팝업"
    CURRENT_CONNECT = "현재 접속자"
    POINT = "포인트"
    POLL = "설문조사"
    POPULAR = "인기 검색어"
    QA = "Q&A"
    SCRAP = "스크랩"
    SEARCH = "검색"
    BOARD_NEW = "최신글"
    AJAX_AUTOSAVE = "자동저장"
    AJAX_GOOD = "좋아요/싫어요"
    VISIT = "방문자"
