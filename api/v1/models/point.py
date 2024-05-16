"""포인트 모델 정의 파일"""
from typing import List

from pydantic import BaseModel

from api.v1.models.pagination import PaginationResponse


class PointBase(BaseModel):
    """포인트 응답 모델"""
    po_content: str
    po_point: int
    po_rel_table: str
    po_rel_id: str
    po_rel_action: str


class PointListResponse(PaginationResponse):
    """포인트 목록 조회 응답 모델"""
    total_points: int  # 전체 포인트 합계
    page_sum_points: dict = {
        "positive": 0,
        "negative": 0
    }  # 페이지 내 포인트 소계
    points: List[PointBase]
