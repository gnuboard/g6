
"""컨텐츠 관련 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Path

from core.models import Content
from api.v1.service.content import ContentServiceAPI


def get_content(
    service: Annotated[ContentServiceAPI, Depends()],
    co_id: Annotated[str, Path(..., title="컨텐츠 ID", description="컨텐츠 ID")]
) -> Content:
    """컨텐츠 1건 조회 의존성 함수"""
    return service.read_content(co_id)
