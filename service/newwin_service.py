"""레이어팝업 관련 기능을 제공하는 서비스 클래스입니다."""
from datetime import datetime
from typing import List
from sqlalchemy import between, select

from core.database import db_session
from core.exception import AlertException
from core.models import NewWin
from service import BaseService


class NewWinService(BaseService):
    """레이어팝업 관련 기능을 제공하는 클래스입니다."""
    current_division = "comm"  # comm, both, shop (현재 커뮤니티만 사용)

    def __init__(self, db: db_session):
        self.db = db

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        return AlertException(detail=detail, status_code=status_code, url=url)

    def fetch_newwins(self, device: str) -> List[NewWin]:
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
