"""컨텐츠 모델 클래스를 정의한 파일입니다."""
from typing import List

from pydantic import BaseModel, ConfigDict, model_validator

from lib.common import get_head_tail_img
from api.v1.models.pagination import PaginationResponse


class ContentResponse(BaseModel):
    """컨텐츠 응답 모델"""
    # 참고 : https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict
    model_config = ConfigDict(
        extra='allow',  # 추가 필드 허용
        from_attributes=True  # 클래스 속성을 필드로 변환
    )

    co_id: str
    co_html: int
    co_subject: str
    co_content: str
    co_seo_title: str
    co_mobile_content: str
    co_hit: int

    co_image_head: str
    co_image_tail: str

    @model_validator(mode='before')
    def init_fields(self) -> 'ContentResponse':
        """
        필드 초기화
        - 상단/하단 이미지경로 설정
        """
        self.co_image_head = get_head_tail_img('content', self.co_id + '_h')['url']
        self.co_image_tail = get_head_tail_img('content', self.co_id + '_t')['url']
        return self


class ContentListResponse(PaginationResponse):
    """컨텐츠 목록 응답 모델"""
    contents: List[ContentResponse]
