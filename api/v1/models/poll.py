"""설문조사 관련 모델 클래스를 정의한 파일입니다."""
from datetime import date, datetime
from typing import List

from fastapi import Body
from pydantic import BaseModel, field_validator

from lib.html_sanitizer import content_sanitizer


class PollBase(BaseModel):
    """설문조사 기본 정보 모델 클래스입니다."""
    po_id: int
    po_subject: str
    po_etc: str
    po_level: int
    po_point: int
    po_date: date
    po_use: int


class Item(BaseModel):
    """설문조사 항목 정보 모델 클래스입니다."""
    subject: str
    count: int
    rank: int
    rate: float


class LatestPollResponse(PollBase):
    """최신 설문조사 정보 모델 클래스입니다."""
    po_poll1: str
    po_poll2: str
    po_poll3: str
    po_poll4: str
    po_poll5: str
    po_poll6: str
    po_poll7: str
    po_poll8: str
    po_poll9: str


class PollEtcResponse(BaseModel):
    """설문조사 기타의견 기본 정보 모델 클래스입니다."""
    pc_id: int
    po_id: int
    mb_id: str
    pc_name: str
    pc_idea: str
    pc_datetime: datetime


class PollResponse(BaseModel):
    """설문조사 응답 정보 모델 클래스입니다."""
    poll: PollBase
    total_vote: int
    items: List[Item]
    etcs: List[PollEtcResponse]
    other_polls: List[PollBase]


class CreatePollEtc(BaseModel):
    """기타의견 생성 요청 모델 클래스입니다."""
    pc_name: str = Body("", title="작성자")
    pc_idea: str = Body(..., title="기타의견")

    @field_validator('pc_idea', mode='after')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """기타의견을 Stored XSS을 방지하도록 처리합니다."""
        return content_sanitizer.get_cleaned_data(v)
