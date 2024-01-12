from fastapi import APIRouter, Depends, File, Form, Path, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException
from core.formclass import ContentForm
from core.models import Content
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token
from lib.template_functions import (
    get_skin_select
)

router = APIRouter()
templates = AdminTemplates()
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_head_tail_img"] = get_head_tail_img

MENU_KEY = "300600"
IMAGE_DIRECTORY = "data/content/"


@router.get("/content_list")
async def content_list(request: Request, db: db_session):
    """
    내용관리 목록
    """
    request.session["menu_key"] = MENU_KEY

    contents = db.scalars(select(Content)).all()

    context = {
        "request": request,
        "contents": contents,
    }
    return templates.TemplateResponse("content_list.html", context)


@router.get("/content_form")
async def content_form_add(request: Request):
    """
    내용추가 폼
    """
    context = {
        "request": request,
        "content": None,
    }
    return templates.TemplateResponse("content_form.html", context)

@router.get("/content_form/{co_id}")
async def content_form_edit(
    request: Request,
    db: db_session,
    co_id: str = Path(...),
):
    """
    내용 수정 폼
    """
    content = db.get(Content, co_id)
    if not content:
        raise AlertException(f"{co_id} : 내용 아이디가 존재하지 않습니다.", 404)

    context = {
        "request": request,
        "content": content,
    }
    return templates.TemplateResponse("content_form.html", context)


@router.post("/content_form_update", dependencies=[Depends(validate_token)])
async def content_form_update(
    request: Request,
    db: db_session,
    action: str = Form(...),
    co_id: str = Form(...),
    form_data: ContentForm = Depends(),
    co_himg: UploadFile = File(None),
    co_timg: UploadFile = File(None),
    co_himg_del: int = Form(None),
    co_timg_del: int = Form(None),
):
    """내용등록 및 수정 처리

    - 내용 등록 및 수정 데이터 저장
    - 이미지파일 저장

    Args:
        request (Request): 
        db (Session, optional): 
        co_id (str): 내용 ID.
        form_data (ContentDataclass): 입력/수정 Form Data.
        co_himg (UploadFile, optional): 상단 이미지 첨부파일. Defaults to File(...).
        co_timg (UploadFile, optional): 하단 이미지 첨부파일. Defaults to File(...).
        co_himg_del (int, optional): 상단 이미지 삭제체크. Defaults to None.
        co_timg_del (int, optional): 하단 이미지 삭제체크. Defaults to None.

    Raises:
        AlertException: 유효한 토큰인지 체크
        AlertException: 아이디 중복체크.
        AlertException: 아이디 존재여부 체크.

    Returns:
        RedirectResponse: 내용 등록/수정 후 상세 폼으로 이동
    """
    if action == "w":
        # ID 중복 검사
        exists_content = db.scalar(select(Content).where(Content.co_id == co_id))
        if exists_content:
            raise AlertException(status_code=400, detail=f"{co_id} : 내용 아이디가 이미 존재합니다.")
        
        # 내용 등록
        content = Content(co_id=co_id, **form_data.__dict__)
        db.add(content)
        db.commit()

    elif action == "u":
        content = db.get(Content, co_id)
        if not content:
            raise AlertException(status_code=404, detail=f"{co_id} : 내용 아이디가 존재하지 않습니다.")

        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            setattr(content, field, value)
        db.commit()

    # 이미지 경로체크 및 생성
    make_directory(IMAGE_DIRECTORY)
    # 이미지 삭제
    delete_image(IMAGE_DIRECTORY, f"{co_id}_h", co_himg_del)
    delete_image(IMAGE_DIRECTORY, f"{co_id}_t", co_timg_del)
    # 이미지 저장
    save_image(IMAGE_DIRECTORY, f"{co_id}_h", co_himg)
    save_image(IMAGE_DIRECTORY, f"{co_id}_t", co_timg)


    return RedirectResponse(url=request.url_for('content_form_edit', co_id=co_id), status_code=302)


@router.get("/content_delete/{co_id}", dependencies=[Depends(validate_token)])
async def content_delete(
    request: Request, 
    db: db_session,
    co_id: str = Path(...)
):
    """
    내용 삭제
    """    
    content = db.get(Content, co_id)
    if not content:
        raise AlertException(status_code=404, detail=f"{co_id}: 내용 아이디가 존재하지 않습니다.")

    # 이미지 삭제
    delete_image(IMAGE_DIRECTORY, f"{co_id}_h")
    delete_image(IMAGE_DIRECTORY, f"{co_id}_t")
    # 내용 삭제
    db.delete(content)
    db.commit()

    return RedirectResponse(url=request.url_for('content_list'), status_code=302)
