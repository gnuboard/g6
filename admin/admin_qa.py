from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from lib.common import *
from common.database import get_db
from common.formclass import QaConfigForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from common.models import QaConfig

router = APIRouter()
templates = AdminTemplates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals['getattr'] = getattr
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["get_head_tail_img"] = get_head_tail_img
templates.env.globals['get_selected'] = get_selected
templates.env.globals["get_skin_select"] = get_skin_select

MENU_KEY = "300500"


@router.get("/qa_config")
def qa_config_form(request: Request, db: Session = Depends(get_db)):
    """
    1:1문의 설정 폼
    """
    request.session["menu_key"] = MENU_KEY

    qa_config = db.query(QaConfig).first()
    return templates.TemplateResponse(
        "qa_config_form.html", {"request": request, "qa_config": qa_config}
    )


@router.post("/qa_config_update")
def qa_config_update(request: Request,
                        db: Session = Depends(get_db),
                        token: str = Form(...),
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
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    qa_config = db.query(QaConfig).first()
    if not qa_config:
        qa_config = QaConfig(**form_data.__dict__)
        db.add(qa_config)
        db.commit()
    else:
        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            setattr(qa_config, field, value)
        db.commit()
    
    return RedirectResponse(url=f"/admin/qa_config", status_code=302)