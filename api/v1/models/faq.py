"""FAQ 모델 클래스를 정의한 파일입니다."""
from pydantic import BaseModel


class FaqMasterResponse(BaseModel):
    """FAQ 분류 응답 모델"""
    fm_id: int
    fm_subject: str
    fm_order: int
    fm_head_html: str
    fm_tail_html: str
    fm_mobile_head_html: str
    fm_mobile_tail_html: str


class FaqResponse(BaseModel):
    """FAQ 응답 모델"""
    fa_id: int
    fm_id: int
    fa_subject: str
    fa_content: str
    fa_order: int
