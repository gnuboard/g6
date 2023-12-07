from fastapi import APIRouter, Depends, File, Form, Path, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from common.database import db_session
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from common.models import FaqMaster, Faq
import shutil

from lib.common import *


router = APIRouter()
templates = AdminTemplates()
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["get_head_tail_img"] = get_head_tail_img
templates.env.globals["now"] = now


FAQ_MENU_KEY = "300700"


@router.get("/faq_master_list")
async def faq_master_list(request: Request, db: db_session):
    """FAQ관리 목록"""
    model = FaqMaster
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_masters = db.query(model).order_by(model.fm_order).all()

    return templates.TemplateResponse(
        "faq_master_list.html", {"request": request, "faq_masters": faq_masters}
    )


@router.get("/faq_master_form")
async def faq_master_add_form(request: Request):
    """FAQ관리 등록 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    return templates.TemplateResponse(
        "faq_master_form.html", {"request": request, "faq_master": None}
    )


@router.post("/faq_master_form_update", dependencies=[Depends(validate_token)])
async def faq_master_add(
        request: Request,
        db: db_session,
        fm_subject: str = Form(...),
        fm_head_html: str = Form(None),
        fm_tail_html: str = Form(None),
        fm_mobile_head_html: str = Form(None),
        fm_mobile_tail_html: str = Form(None),
        fm_order: int = Form(0),
        fm_himg: UploadFile = File(...),
        fm_timg: UploadFile = File(...),
    ):
    """FAQ관리 등록 처리"""
    faq_master = FaqMaster(
        fm_subject=fm_subject
        , fm_head_html=fm_head_html
        , fm_tail_html=fm_tail_html
        , fm_mobile_head_html=fm_mobile_head_html
        , fm_mobile_tail_html=fm_mobile_tail_html
        , fm_order=fm_order
    )
    db.add(faq_master)
    db.commit()
    
    # 이미지 경로 검사 및 생성
    directory_path = "data/faq/"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # 이미지 저장
    if fm_himg and fm_himg.filename:    
        with open(f"{directory_path}{faq_master.fm_id}_h", "wb") as buffer:
            shutil.copyfileobj(fm_himg.file, buffer)
    
    if fm_timg and fm_timg.filename:
        with open(f"{directory_path}{faq_master.fm_id}_t", "wb") as buffer:
            shutil.copyfileobj(fm_timg.file, buffer)

    return RedirectResponse(f"/admin/faq_master_form/{faq_master.fm_id}", status_code=303)


@router.get("/faq_master_form/{fm_id}")
async def faq_master_update_form(fm_id: int, request: Request, db: db_session):
    """FAQ관리 수정 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()

    return templates.TemplateResponse(
        "faq_master_form.html", {"request": request, "faq_master": faq_master}
    )


@router.post("/faq_master_form_update/{fm_id}", dependencies=[Depends(validate_token)])
async def faq_master_update(
        fm_id: int,
        request: Request,
        db: db_session,
        fm_subject: str = Form(...),
        fm_head_html: str = Form(None),
        fm_tail_html: str = Form(None),
        fm_mobile_head_html: str = Form(None),
        fm_mobile_tail_html: str = Form(None),
        fm_order: int = Form(0),
        fm_himg: UploadFile = File(...),
        fm_timg: UploadFile = File(...),
        fm_himg_del: int = Form(None),
        fm_timg_del: int = Form(None),
    ):
    """FAQ관리 수정 처리"""
    faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()

    faq_master.fm_subject = fm_subject
    faq_master.fm_head_html = fm_head_html
    faq_master.fm_tail_html = fm_tail_html
    faq_master.fm_mobile_head_html = fm_mobile_head_html
    faq_master.fm_mobile_tail_html = fm_mobile_tail_html
    faq_master.fm_order = fm_order
    db.commit()

    # 이미지 경로 검사 및 생성
    directory_path = "data/faq/"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # 이미지 삭제
    if fm_himg_del:
        if os.path.exists(f"{directory_path}{fm_id}_h"):
            os.remove(f"{directory_path}{fm_id}_h")
    if fm_timg_del:
        if os.path.exists(f"{directory_path}{fm_id}_t"):
            os.remove(f"{directory_path}{fm_id}_t")
    
    # 이미지 저장
    if fm_himg and fm_himg.filename:    
        with open(f"{directory_path}{fm_id}_h", "wb") as buffer:
            shutil.copyfileobj(fm_himg.file, buffer)
    if fm_timg and fm_timg.filename:    
        with open(f"{directory_path}{fm_id}_t", "wb") as buffer:
            shutil.copyfileobj(fm_timg.file, buffer)

    return RedirectResponse(f"/admin/faq_master_form/{faq_master.fm_id}", status_code=303)


@router.delete("/faq_master_form_delete/{fm_id}")
async def faq_master_delete(
    request: Request,
    db: db_session,
    token: str = Query(...),
    fm_id: int = Path(...),
):
    """FAQ관리 삭제 처리"""
    # 토큰 검사
    # DELETE 요청일 경우, Body에 토큰이 없으므로 쿼리스트링에서 토큰을 얻는다.
    if not check_token(request, token):
        return JSONResponse(status_code=403, content={"message": "토큰이 유효하지 않습니다."})
    
    faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()
    db.delete(faq_master)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "FAQ가 성공적으로 삭제되었습니다."})


@router.get("/faq_list/{fm_id}")
async def faq_list(fm_id: int, request: Request, db: db_session):
    """
    FAQ목록
    """
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()
    faqs = sorted(faq_master.faqs, key=lambda x: x.fa_order)

    return templates.TemplateResponse(
        "faq_list.html", {"request": request, "faq_master": faq_master, "faqs": faqs}
    )


@router.get("/faq_form/{fm_id}")
async def faq_add_form(fm_id: int, request: Request, db: db_session):
    """FAQ항목 등록 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.query(FaqMaster).filter(FaqMaster.fm_id == fm_id).first()

    return templates.TemplateResponse(
        "faq_form.html", {"request": request, "faq_master": faq_master, "faq": None}
    )


@router.post("/faq_form_update/{fm_id}", dependencies=[Depends(validate_token)])
async def faq_add(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
    fa_order: str = Form(...),
    fa_subject: str = Form(...),
    fa_content: str = Form(...),
):
    """FAQ관리 등록 처리"""
    faq = Faq(
        fm_id=fm_id,
        fa_order=fa_order,
        fa_subject=fa_subject,
        fa_content=fa_content,
    )
    db.add(faq)
    db.commit()

    return RedirectResponse(f"/admin/faq_form/{fm_id}/{faq.fa_id}", status_code=303)


@router.get("/faq_form/{fm_id}/{fa_id}")
async def faq_update_form(fa_id: int, request: Request, db: db_session):
    """FAQ항목 수정 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq = db.query(Faq).filter(Faq.fa_id == fa_id).first()
    faq_master = faq.faq_master

    return templates.TemplateResponse(
        "faq_form.html", {"request": request, "faq_master": faq_master, "faq": faq}
    )


@router.post("/faq_form_update/{fm_id}/{fa_id}", dependencies=[Depends(validate_token)])
async def faq_update(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
    fa_id: int = Path(...),
    fa_order: str = Form(...),
    fa_subject: str = Form(...),
    fa_content: str = Form(...),
):
    """FAQ항목 수정 처리"""
    faq = db.query(Faq).filter(Faq.fa_id == fa_id).first()
    faq.fa_subject = fa_subject
    faq.fa_content = fa_content
    faq.fa_order = fa_order
    db.commit()

    return RedirectResponse(f"/admin/faq_form/{fm_id}/{faq.fa_id}", status_code=303)


@router.delete("/faq_form_delete/{fa_id}")
async def faq_delete(
    request: Request,
    db: db_session,
    token: str = Query(...),
    fa_id: int = Path(...),
):
    """FAQ 항목 삭제 처리"""
    # 토큰 검사
    # DELETE 요청일 경우, Body에 토큰이 없으므로 쿼리스트링에서 토큰을 얻는다.
    if not check_token(request, token):
        return JSONResponse(status_code=403, content={"message": "토큰이 유효하지 않습니다."})

    faq = db.query(Faq).filter(Faq.fa_id == fa_id).first()
    db.delete(faq)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "FAQ 항목이 성공적으로 삭제되었습니다."})