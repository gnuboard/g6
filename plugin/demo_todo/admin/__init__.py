from fastapi.params import Depends

from lib.dependencies import check_admin_access
from main import app
from .. import plugin_config
from ..admin.admin_router import admin_router
from ..plugin_config import module_name


# 플러그인의 admin 라우터를 등록한다.
# 관리자는 Depends(check_admin_access) 의존성을 추가 해야 접근권한이 보호된다.
def register_admin_router():
    app.include_router(admin_router, prefix="/admin", tags=[module_name], dependencies=[Depends(check_admin_access)])


def register_admin_menu():
    """관리자 메뉴 등록
    plugin_config.py 에서 관리자메뉴 설정
    Returns:
        dict: 관리자 메뉴
    """
    return getattr(plugin_config, "admin_menu", {})
