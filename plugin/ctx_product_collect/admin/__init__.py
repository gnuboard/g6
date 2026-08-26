from fastapi.params import Depends

from lib.dependency.dependencies import check_admin_access
from main import app
from .. import plugin_config
from ..admin.admin_router import admin_router
from ..plugin_config import module_name


def register_admin_router():
    """관리자 라우터 등록"""
    app.include_router(
        admin_router,
        prefix="/admin",
        tags=[module_name],
        dependencies=[Depends(check_admin_access)],
        include_in_schema=False,
    )


def register_admin_menu():
    """관리자 메뉴 등록"""
    return getattr(plugin_config, "admin_menu", {})
