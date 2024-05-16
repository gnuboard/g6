"""컨텐츠 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from core.models import Content
from lib.common import get_paging_info

from api.v1.dependencies.content import get_content
from api.v1.service.content import ContentServiceAPI
from api.v1.models.content import ContentListResponse, ContentResponse
from api.v1.models.pagination import PagenationRequest
from api.v1.models.response import response_404, response_422

router = APIRouter()


@router.get("/contents",
            summary="컨텐츠 목록 조회",
            responses={**response_422})
async def read_contents(
    service: Annotated[ContentServiceAPI, Depends()],
    data: Annotated[PagenationRequest, Depends()]
) -> ContentListResponse:
    """컨텐츠 목록을 조회합니다."""
    total_records = service.fetch_total_records()
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    contents = service.read_contents(data.offset, data.per_page)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "contents": contents
    }


@router.get("/contents/{co_id}",
            summary="컨텐츠 조회",
            responses={**response_404, **response_422})
async def read_content(
    content: Annotated[Content, Depends(get_content)]
) -> ContentResponse:
    """컨텐츠를 조회합니다."""
    return content
