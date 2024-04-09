from fastapi.params import Depends

from lib.dependency.dependencies import check_admin_access
from main import app
from .. import plugin_config
from ..admin.admin_router import admin_router
from ..plugin_config import module_name



def register_admin_router():
    """관리자에 플러그인 관리자 메뉴를 등록합니다.

    Examples:
        관리자는 Depends(check_admin_access) 의존성을 추가 해야 접근권한이 보호됩니다.
        관리자 라우터의 prefix 는 빈칸이면 안됩니다. 기본값은 /admin 입니다.
    """
    app.include_router(admin_router, prefix="/admin", tags=[module_name], dependencies=[Depends(check_admin_access)], include_in_schema=False)


def register_admin_menu():
    """관리자 메뉴 등록
    plugin_config.py 에서 관리자메뉴 설정
    Returns:
        dict: 관리자 메뉴
    """
    return getattr(plugin_config, "admin_menu", {})
