"""설문조사 관련 모델 클래스를 정의한 파일입니다."""
from typing_extensions import Annotated

from fastapi import Body, Path
from pydantic import BaseModel, field_validator

from lib.html_sanitizer import content_sanitizer


class PatchPollModel(BaseModel):
    """설문조사 참여 요청 모델 클래스입니다."""
    po_id: Annotated[int, Path(..., title="설문조사 ID")]
    item: Annotated[int, Path(..., title="설문항목 번호")]


class CreatePollEtcModel(BaseModel):
    """기타의견 생성 요청 모델 클래스입니다."""
    pc_name: Annotated[str, Body("", title="작성자")]
    pc_idea: Annotated[str, Body(..., title="기타의견")]

    @field_validator('pc_idea', mode='after')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """기타의견을 Stored XSS을 방지하도록 처리합니다."""
        return content_sanitizer.get_cleaned_data(v)
