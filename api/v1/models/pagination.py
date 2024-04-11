"""페이징 모델 클래스를 정의한 파일입니다."""
from fastapi import Query
from pydantic import BaseModel, Field


class PagenationRequest(BaseModel):
    """페이징 요청 모델"""
    page: int = Field(
        Query(default=1,
              ge=1,
              title="페이지 번호",
              description="가져올 결과의 페이지 번호")
    )
    per_page: int = Field(
        Query(default=10,
              ge=1,
              le=100,
              title="출력 수",
              description="페이지 당 결과 수(최대 100)")
    )

    @property
    def offset(self) -> int:
        """페이지 번호에 따른 offset을 계산합니다."""
        return (self.page - 1) * self.per_page


class PaginationResponse(BaseModel):
    """페이징 정보 응답 모델"""
    total_records: int
    total_pages: int
