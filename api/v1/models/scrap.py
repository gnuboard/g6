"""스크랩 관련 모델 클래스를 정의한 파일입니다."""
from datetime import datetime
from typing import List

from fastapi import Body
from pydantic import BaseModel, Field

from api.v1.models.pagination import PaginationResponse


class Board(BaseModel):
    """
    게시판 정보 모델(임시)
    TODO: board.py로 이동 필요
    """
    bo_table: str
    bo_subject: str


class Write(BaseModel):
    """
    글 정보 모델(임시)
    TODO: board.py로 이동 필요
    """
    wr_id: int
    wr_subject: str


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


class ScrapFormResponse(BaseModel):
    """스크랩 등록 페이지 설정 응답 모델"""
    board: Board
    write: Write


class CreateScrapModel(BaseModel):
    """스크랩 생성 모델"""
    wr_content: str = Body(
        default="",
        title="댓글",
        description="스크랩 시 추가할 댓글 내용"
    )
