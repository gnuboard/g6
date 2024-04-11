"""Q&A API 모델 정의 파일입니다."""
from typing_extensions import Annotated

from fastapi import Body, Query
from pydantic import BaseModel, field_validator

from lib.html_sanitizer import content_sanitizer, subject_sanitizer
from api.v1.models.pagination import PagenationRequest


class SearchQaContentModel(PagenationRequest):
    """Q&A 목록 조회 모델"""
    sca: Annotated[str, Query(default="", title="분류")]
    stx: Annotated[str, Query(default="", title="검색어")]
    sfl: Annotated[str, Query(default="", title="검색 필드")]


class QaContentModel(BaseModel):
    """Q&A 등록/수정 모델"""
    qa_email: Annotated[str, Body(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                                  title="이메일", description="이메일 형식에 맞게 입력해주세요.")]
    qa_hp: Annotated[str, Body(None, title="휴대전화번호")]
    qa_category: Annotated[str, Body(None, title="분류")]
    qa_email_recv: Annotated[int, Body(0, title="이메일 수신 여부")]
    qa_sms_recv: Annotated[int, Body(0, title="SMS 수신 여부")]
    qa_html: Annotated[int, Body(1, title="Q&A 내용 형식")]
    qa_subject: Annotated[str, Body(..., title="제목")]
    qa_content: Annotated[str, Body(..., title="내용")]
    qa_parent: Annotated[int, Body(0, title="부모글 번호")]
    qa_related: Annotated[int, Body(0, title="연관 Q&A 번호")]
    # 사용 안할 예정
    # qa_type: Annotated[int, Body(0, title="Q&A 타입", description="0:일반, 1:답변글")]

    qa_1: Annotated[str, Body(..., title="여분필드1")]
    qa_2: Annotated[str, Body(..., title="여분필드2")]
    qa_3: Annotated[str, Body(..., title="여분필드3")]
    qa_4: Annotated[str, Body(..., title="여분필드4")]
    qa_5: Annotated[str, Body(..., title="여분필드5")]

    @field_validator('qa_subject', mode='after')
    @classmethod
    def clean_qa_subject(cls, v: str) -> str:
        """Q&A 제목 Stored XSS 방지 필터링"""
        return subject_sanitizer.get_cleaned_data(v)

    @field_validator('qa_content', mode='after')
    @classmethod
    def clean_qa_content(cls, v: str) -> str:
        """Q&A 제목 Stored XSS 방지 필터링"""
        return content_sanitizer.get_cleaned_data(v)
