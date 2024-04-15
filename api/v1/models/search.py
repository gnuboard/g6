from fastapi import Query
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """검색 요청 모델"""
    sca: str = Field(Query(default="", title="분류", description="검색 분류"))
    stx: str = Field(Query(default="", title="검색어", description="검색어"))
    sfl: str = Field(Query(default="", title="검색 필드", description="검색할 필드"))
