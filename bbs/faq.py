"""FAQ Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query, Request

from core.template import UserTemplates
from lib.common import get_head_tail_img
from service.faq_service import FaqService

router = APIRouter()
templates = UserTemplates()


@router.get("/faq")
@router.get("/faq/{fm_id}")
async def faq_view(
    request: Request,
    faq_service: Annotated[FaqService, Depends()],
    fm_id: int = None,
    stx: Annotated[str, Query()] = None
):
    """
    FAQ 조회
    """
    # faq_master 목록
    faq_masters = faq_service.read_faq_masters()

    # fm_id가 없으면 제일 첫번째 FAQ 카테고리를 가져온다.
    if not fm_id:
        fm_id = faq_masters[0].fm_id

    faq_master = faq_service.read_faq_master(fm_id)
    faqs = faq_service.read_faqs(faq_master, stx)

    himg_data = get_head_tail_img('faq', f"{faq_master.fm_id}_h")
    timg_data = get_head_tail_img('faq', f"{faq_master.fm_id}_t")

    context = {
        "request": request,
        "faq_masters": faq_masters,
        "faq_master": faq_master,
        "faqs": faqs,
        "fm_himg_url": himg_data['url'],
        "fm_timg_url": timg_data['url'],
    }
    return templates.TemplateResponse("/faq/faq.html", context)
