"""자동저장,좋아요/싫어요 모델 정의 파일"""
from enum import Enum
from datetime import datetime
from typing_extensions import Annotated

from fastapi import Body
from pydantic import BaseModel, ConfigDict


class AutoSaveModel(BaseModel):
    """게시글 자동저장 모델"""

    # 추가 필드 허용
    model_config = ConfigDict(extra='allow')

    as_uid: Annotated[int, Body(0, title="자동저장 ID")]
    as_subject: Annotated[str, Body("", max_length=255, title="제목")]
    as_content: Annotated[str, Body("", title="내용")]


class ResponseAutoSaveModel(BaseModel):
    """자동저장글 응답 모델"""
    mb_id: str
    as_uid: int
    as_content: str
    as_subject: str
    as_id: int
    as_datetime: datetime

    class Config:
        from_attributes = True


class ResponseAutoSaveCountModel(BaseModel):
    """자동저장글 개수 응답 모델"""
    count: int


class ResponseAutoSaveDeleteModel(BaseModel):
    """자동저장글 삭제 응답 모델"""
    result: str


class GoodType(Enum):
    """좋아요/싫어요 타입 정의"""
    GOOD = 'good'
    NOGOOD = 'nogood'


class ResponseGoodModel(BaseModel):
    """좋아요/싫어요 응답 모델"""
    status: str
    message: str
    good: int
    nogood: int


class Message(BaseModel):
    """메시지 응답 모델 (API Docs)"""
    message: str


responses = {
    403: {"model": Message},
    404: {"model": Message},
    409: {"model": Message},
}
