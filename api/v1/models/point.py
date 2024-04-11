"""포인트 모델 정의 파일"""
from typing import List

from pydantic import BaseModel

from api.v1.models.pagination import PaginationResponse


class ResponsePointModel(BaseModel):
    """포인트 응답 모델"""
    po_content: str
    po_point: int
    po_rel_table: str
    po_rel_id: str
    po_rel_action: str

    class Config:
        from_attributes = True


class ResponsePointListModel(PaginationResponse):
    """포인트 목록 조회 응답 모델"""
    sum_points: dict
    points: List[ResponsePointModel]
