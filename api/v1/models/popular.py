"""인기 검색어 관련 모델 클래스를 정의한 파일입니다."""
from datetime import date
from fastapi import Body, Query
from pydantic import BaseModel, Field


class CreatePopularRequest(BaseModel):
    """인기 검색어 등록 요청 모델"""
    fields: str = Body(..., title="검색 필드", description="검색 필드")
    word: str = Body(..., title="검색어", description="검색어")


class PopularRequest(BaseModel):
    """인기 검색어 요청 모델"""
    limit: int = Field(Query(default=10, title="조회 갯수", description="조회 갯수"))
    day: int = Field(Query(default=3, title="기간", description="오늘부터 {day}일 전"))


class PopularResponse(BaseModel):
    """인기 검색어 응답 모델"""
    pp_word: str
    count: int
