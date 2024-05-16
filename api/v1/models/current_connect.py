"""현재 접속자 모델 클래스를 정의한 파일입니다."""
from datetime import datetime
from typing import List, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from api.v1.models.pagination import PagenationRequest, PaginationResponse


class CurrentConnectListRequest(PagenationRequest):
    """현재 접속중인 회원 목록 조회 요청 모델"""
    only_member: str = Field(
        Query(default="N",
             title="접속 회원만 표시",
             description="Y: 접속 회원만 표시, N: 전체 표시",
             example="N"))


class CurrentConnectResponse(BaseModel):
    """현재 접속중인 회원 정보 모델"""
    model_config = ConfigDict(from_attributes=True)

    lo_id: int
    lo_ip: str
    mb_id: Union[str, None]
    mb_nick: Union[str, None]
    mb_email: Union[str, None]
    mb_homepage: Union[str, None]
    lo_datetime: datetime
    lo_location: str
    lo_url: str


class CurrentConnectListResponse(PaginationResponse):
    """현재 접속중인 회원 목록 조회 응답 모델"""
    logins: List[CurrentConnectResponse]
