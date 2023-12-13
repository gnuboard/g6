from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from common.database import db_session
from common.formclass import QaConfigForm
from common.models import QaConfig
from lib.common import *
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names


router = APIRouter()
templates = AdminTemplates()
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["get_skin_select"] = get_skin_select


QA_MENU_KEY = "300500"


@router.get("/qa_config")
async def qa_config_form(request: Request, db: db_session):
    """
    1:1문의 설정 폼
    """
    request.session["menu_key"] = QA_MENU_KEY

    qa_config = db.scalar(select(QaConfig))

    return templates.TemplateResponse(
        "qa_config_form.html", {"request": request, "qa_config": qa_config}
    )


@router.post("/qa_config_update", dependencies=[Depends(validate_token)])
def qa_config_update(
    request: Request,
    db: db_session,
    form_data: QaConfigForm = Depends()
):
    """1:1문의 설정 등록/수정 처리

    Args:
        token (str): 입력/수정/삭제 변조 방지 토큰.
        form_data (QaConfigForm): 입력/수정 Form Data.

    Raises:
        AlertException: 토큰 유효성 검사

    Returns:
        RedirectResponse: 1:1문의 설정 등록/수정 후 폼으로 이동
    """
    qa_config = db.scalar(select(QaConfig))
    # 등록
    if not qa_config:
        qa_config = QaConfig(**form_data.__dict__)
        db.add(qa_config)
        db.commit()
    # 수정        
    else:
        for field, value in form_data.__dict__.items():
            setattr(qa_config, field, value)
        db.commit()
    
    return RedirectResponse("/admin/qa_config", status_code=302)