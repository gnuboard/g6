"""쪽지 모델"""
from datetime import datetime
from typing import List
from typing_extensions import Annotated

from fastapi import Path
from pydantic import BaseModel, PrivateAttr, field_validator

from core.models import Member
from lib.html_sanitizer import content_sanitizer as sanitizer

from api.v1.models import ViewPageModel, ResponsePageListModel


class ResponseMemoModel(BaseModel):
    me_id: int
    me_recv_mb_id: str
    me_send_mb_id: str
    me_send_datetime: datetime
    me_read_datetime: datetime
    me_memo: str
    me_send_id: int
    me_type: str
    me_send_ip: str

    # target_mb_id: str

    class Config:
        from_attributes = True


class ViewMemoListModel(ViewPageModel):
    me_type: Annotated[str, Path(title="쪽지 유형",
                                 description="recv: 받은 쪽지, send: 보낸 쪽지",
                                 pattern="^(recv|send)?$")] = "recv"


class ResponseMemoListModel(ResponsePageListModel):
    total_records: int
    total_pages: int
    memos: List[ResponseMemoModel]


class SendMemoModel(BaseModel):
    """쪽지 전송 시 필요한 정보를 정의합니다."""
    _send_mb_ids: List[str] = PrivateAttr()
    _send_members: List[Member] = PrivateAttr()
    _send_point: int = PrivateAttr()

    me_recv_mb_id: str
    me_memo: str

    @field_validator('me_recv_mb_id', mode='after')
    @classmethod
    def check_me_recv_mb_id(cls, v: str):
        """쪽지를 보낼 회원 아이디를 분리합니다."""
        cls._send_mb_ids = v.replace(" ", "").split(',')
        return v

    @field_validator('me_memo', mode='after')
    @classmethod
    def sanitize_me_memo(cls, v: str):
        """쪽지 내용을 정제합니다."""
        return sanitizer.get_cleaned_data(v)

    @property
    def send_mb_ids(self):
        return self._send_mb_ids

    @property
    def send_members(self):
        return self._send_members

    @send_members.setter
    def send_members(self, value):
        self._send_members = value

    @property
    def send_point(self):
        return self._send_point

    @send_point.setter
    def send_point(self, value):
        self._send_point = value

    class Config:
        from_attributes = True
