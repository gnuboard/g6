"""방문자 관련 모델 클래스를 정의한 파일입니다."""
from pydantic import BaseModel


class VisitTotalResponse(BaseModel):
    """방문자 집계 정보 모델"""
    today: int
    yesterday: int
    max: int
    total: int
