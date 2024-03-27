"""컨텐츠 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path

from lib.common import get_head_tail_img, get_paging_info

from api.v1.lib.content import ContentServiceAPI
from api.v1.models import ViewPageModel, responses, responses_403

router = APIRouter()


@router.get("/contents",
            summary="컨텐츠 목록 조회",
            # response_model=ResponseMemoListModel
            responses={**responses_403})
async def read_contents(
    content_service: Annotated[ContentServiceAPI, Depends()],
    data: Annotated[ViewPageModel, Depends()]
):
    """컨텐츠 목록을 조회합니다."""
    total_records = content_service.fetch_total_records()
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    contents = content_service.read_contents(
        paging_info["offset"],
        data.per_page
    )

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "contents": contents
    }


@router.get("/contents/{co_id}",
            summary="컨텐츠 조회",
            # response_model=ResponseMemoModel,
            responses={**responses})
async def read_content(
    content_service: Annotated[ContentServiceAPI, Depends()],
    co_id: Annotated[str, Path(..., title="컨텐츠 ID")]
):
    """컨텐츠를 조회합니다."""
    content = content_service.read_content(co_id)
    head_img = get_head_tail_img('content', content.co_id + '_h')
    tail_img = get_head_tail_img('content', content.co_id + '_t')

    return {
        "content": content,
        "co_himg_url": head_img['url'],
        "co_timg_url": tail_img['url'],
    }
