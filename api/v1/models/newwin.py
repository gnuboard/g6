"""레이어 팝업 모델 클래스를 정의한 파일입니다."""
from datetime import datetime
from enum import Enum

from fastapi import Query
from pydantic import BaseModel, Field

class Device(Enum):
    """접속기기"""
    PC = 'pc'
    MOBILE = 'mobile'


class DeviceRequest(BaseModel):
    """레이어팝업 조회 API 요청 모델"""
    device: Device = Field(Query(default="pc", title="접속기기", description="접속기기"))


class NewwinResponse(BaseModel):
    """"레이어팝업 조회 API 응답 모델"""
    nw_id: int
    nw_division: str
    nw_device: str
    nw_begin_time: datetime
    nw_end_time: datetime
    nw_disable_hours: int
    nw_left: int
    nw_top: int
    nw_height: int
    nw_width: int
    nw_subject: str
    nw_content: str
