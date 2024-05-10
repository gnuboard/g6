"""레이어팝업 관련 기능을 제공하는 서비스 클래스입니다."""
from datetime import datetime
from typing import List
from cachetools import LFUCache, cached
from cachetools.keys import hashkey
from fastapi import Request
from sqlalchemy import between, select
from sqlalchemy.orm import Session

from core.database import db_session
from core.exception import AlertException
from core.models import NewWin
from service import BaseService


class NewWinService(BaseService):
    """레이어팝업 관련 기능을 제공하는 클래스입니다."""
    current_division = "comm"  # comm, both, shop (현재 커뮤니티만 사용)

    def __init__(self, request: Request, db: Session):
        self.request = request
        self.db = db

    @classmethod
    async def async_init(cls, request: Request, db: db_session):
        """비동기로 클래스를 초기화하는 함수"""
        instance = cls(request, db)
        return instance

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        return AlertException(detail=detail, status_code=status_code, url=url)

    @cached(LFUCache(maxsize=256), key=lambda self, device="pc": hashkey("newwins", device))
    def fetch_newwins(self, device: str = "pc") -> List[NewWin]:
        """
        레이어 팝업 목록을 데이터베이스에서 조회합니다.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        newwins = self.db.scalars(
            select(NewWin).where(
                between(now, NewWin.nw_begin_time, NewWin.nw_end_time),
                NewWin.nw_device.in_(["both", device]),
                NewWin.nw_division.in_(["both", self.current_division]),
            ).order_by(NewWin.nw_id)
        ).all()

        return newwins

    def get_newwins_except_cookie(self):
        """
        쿠키에 저장된 팝업을 제외한 레이어 팝업 목록을 반환하는 함수
        """
        device = getattr(self.request.state, "device", "pc")
        newwins = self.fetch_newwins(device)

        # "hd_pops_" + nw_id 이름으로 선언된 쿠키가 있는지 확인하고 있다면 팝업을 제거
        return [newwin for newwin in newwins
                if not self.request.cookies.get("hd_pops_" + str(newwin.nw_id))]
