from fastapi import APIRouter
from starlette.requests import Request

from core.plugin import get_admin_plugin_menus, get_all_plugin_module_names
from core.template import AdminTemplates
from lib.common import get_admin_menus, get_client_ip
from lib.template_functions import (
    get_editor_select, get_member_id_select, get_member_level_select,
    get_selected, get_skin_select, option_array_checked,
)
from ..plugin_config import module_name, admin_router_prefix, TEMPLATE_PATH

templates = AdminTemplates()
templates.env.globals["admin_menus"] = get_admin_menus()
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_client_ip"] = get_client_ip
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

admin_router = APIRouter(prefix=admin_router_prefix)


@admin_router.get("/")
async def index(request: Request):
    """CTX 상품수집 관리자 대시보드"""
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "_dashboard"

    context = {
        "request": request,
        "title": "CTX 상품수집",
        "module_name": module_name,
    }
    return templates.TemplateResponse(
        f"{TEMPLATE_PATH}/admin/index.html", context
    )


@admin_router.get("/collect")
async def collect(request: Request):
    """CTX 상품수집 - 수집 페이지"""
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "_collect"

    context = {
        "request": request,
        "title": "수집",
        "module_name": module_name,
    }
    return templates.TemplateResponse(
        f"{TEMPLATE_PATH}/admin/collect.html", context
    )
