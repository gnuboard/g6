from fastapi import APIRouter
from starlette.requests import Request

from core.plugin import get_admin_plugin_menus, get_all_plugin_module_names
from core.template import AdminTemplates
from lib.common import get_admin_menus, get_client_ip
from lib.template_functions import (
    get_editor_select, get_member_id_select, get_member_level_select,
    get_selected, get_skin_select, option_array_checked
)
from . import plugin_config
from ..plugin_config import module_name, admin_router_prefix

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

admin_router = APIRouter(prefix=admin_router_prefix, tags=['demo_admin'])


@admin_router.get("/test_demo_admin")
async def show(request: Request):
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "1"

    return {
        "message": "Hello Admin Demo Plugin!",
        "pacakge": __package__,
        "__file__": __file__,
        "__name__": __name__,
    }


@admin_router.get("/test_demo_admin_template")
async def show(request: Request):
    request.session["menu_key"] = module_name
    request.session["plugin_submenu_key"] = module_name + "2"

    context = {
        "request": request,
        "title": "Hello Admin demo Plugin!",
        "content": f"Hello {module_name}",
        "module_name": module_name,
    }
    return templates.TemplateResponse(f"{plugin_config.TEMPLATE_PATH}/admin/admin_demo.html", context)
