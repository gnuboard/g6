from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from core.database import db_session
from core.formclass import QaConfigForm
from core.models import QaConfig
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token
from lib.template_functions import get_skin_select


router = APIRouter()
templates = AdminTemplates()
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