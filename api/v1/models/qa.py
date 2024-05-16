"""Q&A API 모델 정의 파일입니다."""
from datetime import datetime
from typing import List, Union

from fastapi import Body
from pydantic import BaseModel, EmailStr, field_validator

from lib.html_sanitizer import content_sanitizer, subject_sanitizer
from api.v1.models.search import SearchRequest
from api.v1.models.pagination import PagenationRequest, PaginationResponse


class QaConfigResponse(BaseModel):
    """Q&A 설정 조회 응답 모델"""
    qa_title: str
    qa_category: str
    qa_use_email: int
    qa_req_email: int
    qa_use_hp: int
    qa_req_hp: int
    qa_use_sms: int
    qa_use_editor: int
    qa_subject_len: int
    qa_mobile_subject_len: int
    qa_page_rows: int
    qa_mobile_page_rows: int
    qa_image_width: int
    qa_upload_size: int
    qa_content_head: str
    qa_content_tail: str
    qa_mobile_content_head: str
    qa_mobile_content_tail: str
    qa_insert_content: str


class QaContentBase(BaseModel):
    """Q&A 기본 모델"""
    qa_id: int
    qa_parent: int
    mb_id: str
    qa_name: str
    qa_type: int
    qa_category: str
    qa_subject: str
    qa_content: str
    qa_status: int
    qa_file1: str
    qa_source1: str
    qa_file2: str
    qa_source2: str
    qa_ip: str
    qa_datetime: datetime


class QaContent(QaContentBase):
    """Q&A 응답 모델"""
    qa_related: int
    qa_email: str
    qa_hp: str
    qa_email_recv: int
    qa_sms_recv: int
    qa_html: int
    qa_1: str
    qa_2: str
    qa_3: str
    qa_4: str
    qa_5: str


class QaContentList(SearchRequest, PagenationRequest):
    """Q&A 목록 조회 모델"""
    pass


class QaContentListResponse(PaginationResponse):
    """Q&A 목록 응답 모델"""
    qa_contents: List[QaContentBase]


class QaContentResponse(BaseModel):
    """Q&A 상세 조회 응답 모델"""
    qa_content: QaContent
    answer: Union[QaContentBase, None]
    prev: Union[QaContentBase, None]
    next: Union[QaContentBase, None]
    related: List[QaContentBase]


class QaContentData(BaseModel):
    """Q&A 등록/수정 모델"""
    qa_subject: str = Body(..., title="제목")
    qa_content: str = Body(..., title="내용")
    qa_related: int = Body(0, title="연관 Q&A 번호")
    qa_email: EmailStr = Body(None,
                              title="이메일", description="이메일 형식에 맞게 입력해주세요.")
    qa_hp: str = Body(None, title="휴대전화번호")
    qa_category: str = Body(None, title="분류")
    qa_email_recv: int = Body(0, title="이메일 수신 여부")
    qa_sms_recv: int = Body(0, title="SMS 수신 여부")
    qa_html: int = Body(1, title="Q&A 내용 형식")

    qa_1: str = Body(None, title="여분필드1")
    qa_2: str = Body(None, title="여분필드2")
    qa_3: str = Body(None, title="여분필드3")
    qa_4: str = Body(None, title="여분필드4")
    qa_5: str = Body(None, title="여분필드5")

    # 관리자만 답변을 등록할 수 있으므로 주석 처리
    # qa_parent: int = Body(0, title="부모글 번호")
    # 사용 안할 예정
    # qa_type: Annotated[int, Body(0, title="Q&A 타입", description="0:일반, 1:답변글")]

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
