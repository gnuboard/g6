from datetime import datetime
from typing import List

from pydantic import BaseModel, PrivateAttr, field_validator


class CreateMemoModel(BaseModel):
    _mb_ids: List[str] = PrivateAttr()
    me_recv_mb_id: str
    me_memo: str

    @field_validator('me_recv_mb_id', mode='after')
    @classmethod
    def check_me_recv_mb_id(cls, v: str):
        cls._mb_ids = v.replace(" ", "").split(',')
        return v


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

    target_mb_id: str

    class Config:
        from_attributes = True