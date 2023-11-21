from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from lib.common import *
from common.database import get_db
from common.models import FaqMaster, Faq

router = APIRouter()
templates = MyTemplates(directory=TEMPLATES_DIR)


@router.get("/faq")
@router.get("/faq/{fm_id}")
def faq_view(request: Request, fm_id: int = None, db: Session = Depends(get_db)):
    '''
    FAQ 보기
    '''
    # fm_id가 없으면 제일 첫번째 FAQ 카테고리를 가져온다.
    if not fm_id:
        faq_master = db.query(FaqMaster).order_by(FaqMaster.fm_order.asc()).first()
    else:
        faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()

    if not faq_master:
        raise AlertException(status_code=404, detail=f"FAQ 카테고리가 없습니다.")
    
    # faq_master 목록
    faq_masters = db.query(FaqMaster).order_by(FaqMaster.fm_order.asc()).all()
    # faq_master에 속한 faq 목록
    queryset = db.query(Faq).filter(Faq.fa_id.in_([faq.fa_id for faq in faq_master.faqs]))
    # 제목과 내용 중 검색어가 있으면 검색한다.
    if request.state.stx:
        queryset = queryset.filter(Faq.fa_subject.like(f"%{request.state.stx}%") | Faq.fa_content.like(f"%{request.state.stx}%"))
    faqs = queryset.order_by(Faq.fa_order.asc()).all()

    # 상단/하단 이미지가 있으면 이미지를 출력하고 없으면 내용의 첫번째 이미지를 출력한다.
    himg_data = get_head_tail_img('faq', f"{faq_master.fm_id}_h")
    fm_himg_url = himg_data['img_url'] if himg_data['img_exists'] else ""

    timg_data = get_head_tail_img('faq', f"{faq_master.fm_id}_t")
    fm_timg_url = timg_data['img_url'] if timg_data['img_exists'] else ""

    context = {
        "request": request,
        "faq_masters": faq_masters,
        "faq_master": faq_master,
        "faqs": faqs,
        "fm_himg_url": fm_himg_url,
        "fm_timg_url": fm_timg_url,
    }

    return templates.TemplateResponse(f"{request.state.device}/faq/faq.html", context)