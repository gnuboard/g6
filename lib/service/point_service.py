"""포인트 관련 기능을 제공하는 서비스 모듈입니다."""
from typing import List

from fastapi import Request

from core.database import db_session
from core.exception import AlertException
from core.models import Member, Point
from lib.service import BaseService


class PointService(BaseService):
    """포인트 서비스 클래스"""
    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise AlertException(status_code=status_code, detail=detail, url=url)

    def fetch_total_records(self, member: Member) -> int:
        """
        포인트 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        return member.points.count()

    def fetch_points(self, member: Member, offset: int = 0, records_per_page: int = 10):
        """
        포인트 목록을 데이터베이스에서 조회합니다.
        """
        return (member.points
                .order_by(Point.po_id.desc())
                .offset(offset).limit(records_per_page)
                .all())

    def calculate_sum(self, points: List[Point]) -> dict:
        """
        포인트 목록의 합계를 계산합니다.
        """
        positive = 0
        negative = 0
        for point in points:
            if point.po_point > 0:
                positive += point.po_point
            else:
                negative += point.po_point

        return {"positive": positive, "negative": negative}
