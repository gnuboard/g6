"""메뉴 모델 클래스를 정의한 파일입니다."""
from typing import List

from pydantic import BaseModel


class MenuBase(BaseModel):
    """메뉴 응답 기본 모델"""
    me_id: int
    me_name: str
    me_link: str
    me_order: int
    me_mobile_use: int
    me_target: str
    me_code: str
    me_use: int


class MenuResponse(MenuBase):
    """메뉴 응답 모델"""
    sub: List[MenuBase]
