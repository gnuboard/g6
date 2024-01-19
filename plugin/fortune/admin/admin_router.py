from typing import Optional

from fastapi import APIRouter, Depends, Form, Path
from sqlalchemy import select, insert, update, delete
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from core.database import db_session
from core.plugin import get_admin_plugin_menus, get_all_plugin_module_names
from core.template import ADMIN_TEMPLATES_DIR, AdminTemplates
from lib.common import get_admin_menus, get_client_ip
from lib.dependencies import validate_token
from lib.template_functions import (
    get_editor_select, get_member_id_select, get_member_level_select,
    get_selected, get_skin_select, option_array_checked
)
from .. import plugin_config
from ..models import Fortune
from ..plugin_config import module_name, admin_router_prefix

templates = AdminTemplates()
admin_router = APIRouter(prefix=f'/{admin_router_prefix}', tags=['demo_admin'])

@admin_router.get("/list")
def show_list(
    request: Request,
    db: db_session,
):
    request.session["menu_key"] = module_name

    fortunes = db.scalars(select(Fortune)).all()

    context = {
        "request": request,
        "fortunes": fortunes,
    }
    return templates.TemplateResponse(f"{plugin_config.TEMPLATE_PATH}/admin/list.html", context)


@admin_router.post("/delete", dependencies=[Depends(validate_token)])
def delete_fortune(
    request: Request,
    db: db_session,
    ids: list = Form(..., alias='chk[]'),
):
    db.execute(
        delete(Fortune).where(Fortune.id.in_(ids))
    )
    db.commit()

    return RedirectResponse(f"/admin/fortune/list", status_code=302)
