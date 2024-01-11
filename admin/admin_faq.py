import shutil

from fastapi import APIRouter, Depends, File, Form, Path, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from core.database import db_session
from core.formclass import FaqMasterForm, FaqForm
from core.models import FaqMaster, Faq
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token

router = APIRouter()
templates = AdminTemplates()
templates.env.globals["get_head_tail_img"] = get_head_tail_img

FAQ_MENU_KEY = "300700"
FAQ_FILE_PATH = "data/faq"


@router.get("/faq_master_list")
async def faq_master_list(request: Request, db: db_session):
    """FAQ관리 목록"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_masters = db.scalars(
        select(FaqMaster).order_by(FaqMaster.fm_order)
    ).all()

    context = {
        "request": request,
        "faq_masters": faq_masters
    }
    return templates.TemplateResponse("faq_master_list.html", context)


@router.get("/faq_master_form")
async def faq_master_add_form(request: Request):
    """FAQ관리 등록 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    context = {
        "request": request,
        "faq_master": None
    }
    return templates.TemplateResponse("faq_master_form.html", context)


@router.post("/faq_master_form_update", dependencies=[Depends(validate_token)])
async def faq_master_add(
    request: Request,
    db: db_session,
    form: FaqMasterForm = Depends(),
    fm_himg: UploadFile = File(None),
    fm_timg: UploadFile = File(None),
):
    """FAQ관리 등록 처리"""
    faq_master = FaqMaster(**form.__dict__)
    db.add(faq_master)
    db.commit()

    # 이미지 경로 검사 및 생성
    fm_id = faq_master.fm_id
    if not os.path.exists(FAQ_FILE_PATH):
        os.makedirs(FAQ_FILE_PATH)

    # 이미지 저장
    if fm_himg and fm_himg.filename:
        with open(f"{FAQ_FILE_PATH}{fm_id}_h", "wb") as buffer:
            shutil.copyfileobj(fm_himg.file, buffer)

    if fm_timg and fm_timg.filename:
        with open(f"{FAQ_FILE_PATH}{fm_id}_t", "wb") as buffer:
            shutil.copyfileobj(fm_timg.file, buffer)

    return RedirectResponse(f"/admin/faq_master_form/{fm_id}", 303)


@router.get("/faq_master_form/{fm_id}")
async def faq_master_update_form(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
):
    """FAQ관리 수정 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.get(FaqMaster, fm_id)

    context = {
        "request": request,
        "faq_master": faq_master
    }
    return templates.TemplateResponse("faq_master_form.html", context)


@router.post("/faq_master_form_update/{fm_id}", dependencies=[Depends(validate_token)])
async def faq_master_update(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
    form: FaqMasterForm = Depends(),
    fm_himg: UploadFile = File(...),
    fm_timg: UploadFile = File(...),
    fm_himg_del: int = Form(None),
    fm_timg_del: int = Form(None),
):
    """FAQ관리 수정 처리"""
    faq_master = db.get(FaqMaster, fm_id)
    for field, value in form.__dict__.items():
        setattr(faq_master, field, value)
    db.commit()

    file_path_h = os.path.join(FAQ_FILE_PATH, f"{fm_id}_h")
    file_path_t = os.path.join(FAQ_FILE_PATH, f"{fm_id}_t")

    # 이미지 경로 검사 및 생성
    if not os.path.exists(FAQ_FILE_PATH):
        os.makedirs(FAQ_FILE_PATH)

    # 이미지 삭제
    if fm_himg_del and os.path.exists(file_path_h):
        os.remove(file_path_h)
    if fm_timg_del and os.path.exists(file_path_t):
        os.remove(file_path_t)

    # 이미지 저장
    if getattr(fm_himg, "filename"):
        with open(file_path_h, "wb") as buffer:
            shutil.copyfileobj(fm_himg.file, buffer)
    if getattr(fm_timg, "filename"):
        with open(file_path_t, "wb") as buffer:
            shutil.copyfileobj(fm_timg.file, buffer)

    return RedirectResponse(f"/admin/faq_master_form/{fm_id}", 303)


@router.delete("/faq_master_form_delete/{fm_id}", dependencies=[Depends(validate_token)])
async def faq_master_delete(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
):
    """FAQ관리 삭제 처리"""
    faq_master = db.get(FaqMaster, fm_id)
    db.delete(faq_master)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "FAQ가 성공적으로 삭제되었습니다."})


@router.get("/faq_list/{fm_id}")
async def faq_list(
    request: Request,
    db: db_session,
    fm_id: int = Path(...)
):
    """FAQ목록"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.get(FaqMaster, fm_id)
    faqs = sorted(faq_master.faqs, key=lambda x: x.fa_order)

    context = {
        "request": request,
        "faq_master": faq_master,
        "faqs": faqs
    }
    return templates.TemplateResponse("faq_list.html", context)


@router.get("/faq_form/{fm_id}")
async def faq_add_form(
    request: Request,
    db: db_session,
    fm_id: int = Path(...)
):
    """FAQ항목 등록 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq_master = db.get(FaqMaster, fm_id)

    context = {
        "request": request,
        "faq_master": faq_master,
        "faq": None
    }
    return templates.TemplateResponse("faq_form.html", context)


@router.post("/faq_form_update/{fm_id}", dependencies=[Depends(validate_token)])
async def faq_add(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
    form: FaqForm = Depends(),
):
    """FAQ관리 등록 처리"""
    faq_master = db.get(FaqMaster, fm_id)
    faq = Faq(fm_id=faq_master.fm_id, **form.__dict__)
    db.add(faq)
    db.commit()

    return RedirectResponse(f"/admin/faq_form/{fm_id}/{faq.fa_id}", status_code=303)


@router.get("/faq_form/{fm_id}/{fa_id}")
async def faq_update_form(fa_id: int, request: Request, db: db_session):
    """FAQ항목 수정 폼"""
    request.session["menu_key"] = FAQ_MENU_KEY

    faq = db.get(Faq, fa_id)
    faq_master = faq.faq_master

    context = {
        "request": request,
        "faq_master": faq_master,
        "faq": faq
    }
    return templates.TemplateResponse("faq_form.html", context)


@router.post("/faq_form_update/{fm_id}/{fa_id}", dependencies=[Depends(validate_token)])
async def faq_update(
    request: Request,
    db: db_session,
    fm_id: int = Path(...),
    fa_id: int = Path(...),
    form: FaqForm = Depends(),
):
    """FAQ항목 수정 처리"""
    faq = db.get(Faq, fa_id)
    for field, value in form.__dict__.items():
        setattr(faq, field, value)
    db.commit()

    return RedirectResponse(f"/admin/faq_form/{fm_id}/{fa_id}", status_code=303)


@router.delete("/faq_form_delete/{fa_id}", dependencies=[Depends(validate_token)])
async def faq_delete(
    request: Request,
    db: db_session,
    fa_id: int = Path(...),
):
    """FAQ 항목 삭제 처리"""
    faq = db.get(Faq, fa_id)
    db.delete(faq)
    db.commit()

    return JSONResponse(status_code=200, content={"message": "FAQ 항목이 성공적으로 삭제되었습니다."})
