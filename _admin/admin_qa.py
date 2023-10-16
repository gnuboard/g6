import shutil
from dataclasses import dataclass
from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from database import get_db
import models
import datetime
from common import *

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
# templates.env.globals['today'] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals["now"] = now
templates.env.globals['getattr'] = getattr
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_head_tail_img"] = get_head_tail_img
templates.env.globals['get_selected'] = get_selected
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["generate_one_time_token"] = generate_one_time_token


MENU_KEY = "300600"

@dataclass
class QaConfigDataclass:
    """1:1문의 설정 폼 데이터
        - 그누보드5에서 사라지는 기능(변수)
            1. 상단 파일 경로 (qa_include_head)
            2. 하단 파일 경로 (qa_include_tail)
    """
    qa_title: str = Form(...)
    qa_category: str = Form(None)
    qa_skin: str = Form(None)
    qa_mobile_skin: str = Form(None)
    qa_use_email: int = Form(None)
    qa_req_email: int = Form(None)
    qa_use_hp: int = Form(None)
    qa_req_hp: int = Form(None)
    qa_use_sms: int = Form(None)
    qa_send_number: str = Form(None)
    qa_admin_hp: str = Form(None)
    qa_admin_email: str = Form(None)
    qa_use_editor: int = Form(None)
    qa_subject_len: int = Form(None)
    qa_mobile_subject_len: int = Form(None)
    qa_page_rows: int = Form(None)
    qa_mobile_page_rows: int = Form(None)
    qa_image_width: int = Form(None)
    qa_upload_size: int = Form(None)
    qa_insert_content: str = Form(None)
    qa_include_head: str = Form(None)
    qa_include_tail: str = Form(None)
    qa_content_head: str = Form(None)
    qa_content_tail: str = Form(None)
    qa_mobile_content_head: str = Form(None)
    qa_mobile_content_tail: str = Form(None)
    qa_1_subj: str = Form(None)
    qa_2_subj: str = Form(None)
    qa_3_subj: str = Form(None)
    qa_4_subj: str = Form(None)
    qa_5_subj: str = Form(None)
    qa_1: str = Form(None)
    qa_2: str = Form(None)
    qa_3: str = Form(None)
    qa_4: str = Form(None)
    qa_5: str = Form(None)


@router.get("/qa_config")
def qa_config_form(request: Request, db: Session = Depends(get_db)):
    """
    1:1문의 설정 폼
    """
    request.session["menu_key"] = MENU_KEY

    qa_config = db.query(models.QaConfig).first()
    return templates.TemplateResponse(
        "qa_config_form.html", {"request": request, "qa_config": qa_config}
    )


@router.post("/qa_config_update")
def qa_config_update(request: Request,
                        db: Session = Depends(get_db),
                        token: str = Form(...),
                        form_data: QaConfigDataclass = Depends()
                        ):
    """1:1문의 설정 등록/수정 처리

    Args:
        token (str): 입력/수정/삭제 변조 방지 토큰.
        form_data (QaConfigDataclass): 입력/수정 Form Data.

    Raises:
        HTTPException: 토큰 유효성 검사

    Returns:
        RedirectResponse: 1:1문의 설정 등록/수정 후 폼으로 이동
    """
    if validate_one_time_token(token, 'create'): # 토큰에 등록돤 action이 create라면 신규 등록
        qa_config = models.QaConfig(**form_data.__dict__)
        db.add(qa_config)
        db.commit()

    elif validate_one_time_token(token, 'update'):  # 토큰에 등록된 action이 create가 아니라면 수정
        # 데이터 수정 후 commit
        qa_config = db.query(models.QaConfig).first()
        for field, value in form_data.__dict__.items():
            setattr(qa_config, field, value)
        db.commit()
    
    else: # 토큰 검사 실패
        raise HTTPException(status_code=404, detail=f"{token} : 토큰이 존재하지 않습니다.")

    return RedirectResponse(url=f"/admin/qa_config", status_code=302)