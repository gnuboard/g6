"""FAQ API Router"""
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path, Query

from api.v1.service.faq import FaqServiceAPI
from api.v1.models.faq import FaqMasterResponse, FaqResponse
from api.v1.models.response import response_404, response_422

router = APIRouter()


@router.get("/faqs",
            summary="FAQ 분류 목록 조회")
async def read_faqs(
    service: Annotated[FaqServiceAPI, Depends()],
) -> List[FaqMasterResponse]:
    """FAQ 분류 목록을 조회합니다."""
    return service.read_faq_masters()


@router.get("/faqs/{fm_id}",
            summary="FAQ 분류 > 내용 목록 조회",
            responses={**response_404, **response_422})
async def read_faq(
    service: Annotated[FaqServiceAPI, Depends()],
    fm_id: Annotated[int, Path(title="FAQ 분류 아이디",
                               description="FAQ 분류 아이디")],
    stx: str = Query(None, title="검색어", description="검색어")
) -> List[FaqResponse]:
    """분류에 속한 FAQ 내용 목록을 조회합니다."""
    faq_master = service.read_faq_master(fm_id)

    return service.read_faqs(faq_master, stx)
