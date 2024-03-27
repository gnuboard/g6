"""FAQ API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path, Query

from api.v1.lib.faq import FaqServiceAPI
from api.v1.models import responses

router = APIRouter()


@router.get("/faqs",
            summary="FAQ 목록 조회",
            # response_model=ResponseMemoListModel
            responses={**responses})
async def read_faqs(
    faq_service: Annotated[FaqServiceAPI, Depends()],
):
    """FAQ 목록을 조회합니다."""
    faq_masters = faq_service.read_faq_masters()

    return faq_masters


@router.get("/faqs/{fm_id}",
            summary="FAQ 분류 > 내용 목록 조회",
            # response_model=ResponseMemoListModel
            responses={**responses})
async def read_faq(
    faq_service: Annotated[FaqServiceAPI, Depends()],
    fm_id: Annotated[int, Path(..., title="FAQ 분류 아이디")],
    stx: str = Query(None)
):
    """FAQ 분류에 속한 목록을 조회합니다."""
    faq_master = faq_service.read_faq_master(fm_id)
    faq_master.faqs = faq_service.read_faqs(faq_master, stx)

    return faq_master
