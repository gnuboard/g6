"""스크랩 관련 모델 클래스를 정의한 파일입니다."""
from datetime import datetime
from typing import List

from fastapi import Body
from pydantic import BaseModel, field_validator

from lib.html_sanitizer import content_sanitizer as sanitizer
from api.v1.models.pagination import PaginationResponse


class ScrapBoardResponse(BaseModel):
    """스크랩 페이지 게시판 정보 모델"""
    bo_table: str
    bo_subject: str


class ScrapWriteResponse(BaseModel):
    """스크랩 페이지 글 정보 모델"""
    wr_id: int
    wr_subject: str


class ScrapFormResponse(BaseModel):
    """스크랩 등록 페이지 설정 응답 모델"""
    board: ScrapBoardResponse
    write: ScrapWriteResponse


class CreateScrap(BaseModel):
    """스크랩 생성 모델"""
    wr_content: str = Body(
        default="",
        title="댓글",
        description="스크랩 시 추가할 댓글 내용"
    )

    @field_validator('wr_content', mode='after')
    @classmethod
    def sanitize_wr_content(cls, v: str):
        """댓글 내용 Stored XSS 방지 필터링"""
        return sanitizer.get_cleaned_data(v)


class ScrapResponse(BaseModel):
    """스크랩 응답 모델"""
    ms_id: int
    mb_id: str
    bo_table: str
    wr_id: int
    ms_datetime: datetime

    wr_subject: str
    bo_subject: str


class ScrapListResponse(PaginationResponse):
    """스크랩 목록 응답 모델"""
    scraps: List[ScrapResponse]
