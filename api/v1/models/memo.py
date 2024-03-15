from datetime import datetime
from typing import List
from typing_extensions import Annotated

from fastapi import Path, Query
from pydantic import BaseModel, PrivateAttr, field_validator

from core.models import Member


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


class ViewMemoListModel(BaseModel):
    me_type: Annotated[str, Path(title="쪽지 유형",
                                 description="recv: 받은 쪽지, send: 보낸 쪽지",
                                 pattern="^(recv|send)?$")] = "recv"
    page: Annotated[int, Query(title="페이지 번호")] = 1
    per_page: Annotated[int, Query(title="페이지 당 쪽지 수")] = 10


class ResponseMemoListModel(BaseModel):
    total_records: int
    total_pages: int
    memos: List[ResponseMemoModel]

    class Config:
        from_attributes = True


class SendMemoModel(BaseModel):
    _send_mb_ids: List[str] = PrivateAttr()
    _send_members: List[Member] = PrivateAttr()
    _send_point: int = PrivateAttr()
    me_recv_mb_id: str
    me_memo: str

    @field_validator('me_recv_mb_id', mode='after')
    @classmethod
    def check_me_recv_mb_id(cls, v: str):
        cls._send_mb_ids = v.replace(" ", "").split(',')
        return v

    class Config:
        from_attributes = True
