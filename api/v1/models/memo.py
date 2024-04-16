"""쪽지 모델 클래스를 정의한 파일입니다."""
from datetime import datetime
from typing import List, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from core.models import Member
from lib.html_sanitizer import content_sanitizer as sanitizer

from api.v1.models.pagination import PagenationRequest, PaginationResponse


class MemoList(PagenationRequest):
    """쪽지 목록 조회 요청 모델"""
    me_type: str = Field(
        Query(default="recv",
             title="쪽지 유형",
             description="recv: 받은 쪽지, send: 보낸 쪽지",
             pattern="^(recv|send)?$")
    )

class MemoBase(BaseModel):
    """쪽지 응답 기본 모델"""
    model_config = ConfigDict(
        extra='allow',  # 추가 필드 허용
        from_attributes=True  # 클래스 속성을 필드로 변환
    )
    me_id: int
    me_recv_mb_id: str
    me_send_mb_id: str
    me_send_datetime: datetime
    me_read_datetime: datetime
    me_memo: str
    me_send_id: int
    me_type: str
    me_send_ip: str


class MemoResponse(BaseModel):
    """쪽지 조회 응답 모델"""
    memo: MemoBase
    prev_memo: Union[MemoBase, None]
    next_memo: Union[MemoBase, None]


class MemoListResponse(PaginationResponse):
    """쪽지 목록 조회 응답 모델"""
    memos: List[MemoBase]


class SendMemo(BaseModel):
    """쪽지 전송 시 필요한 정보를 정의합니다."""
    model_config = ConfigDict(
        extra='allow',  # 추가 필드 허용
        from_attributes=True  # 클래스 속성을 필드로 변환
    )

    _mb_ids: List[str] = PrivateAttr()
    _members: List[Member] = PrivateAttr()
    _point: int = PrivateAttr()

    me_recv_mb_id: str
    me_memo: str

    @field_validator('me_recv_mb_id', mode='after')
    @classmethod
    def check_me_recv_mb_id(cls, v: str):
        """쪽지를 보낼 회원 아이디를 분리합니다."""
        cls._mb_ids = v.replace(" ", "").split(',')
        return v

    @field_validator('me_memo', mode='after')
    @classmethod
    def sanitize_me_memo(cls, v: str):
        """쪽지 내용 Stored XSS 방지 필터링"""
        return sanitizer.get_cleaned_data(v)

    @property
    def mb_ids(self):
        return self._mb_ids

    @property
    def members(self):
        return self._members

    @members.setter
    def members(self, value):
        self._members = value

    @property
    def point(self):
        return self._point

    @point.setter
    def point(self, value):
        self._point = value
