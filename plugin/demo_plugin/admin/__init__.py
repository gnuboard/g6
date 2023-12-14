from ..admin.admin_router import admin_router
from ..plugin_info import module_name
from main import app


# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.

def register_admin_router():
    """관리자 등록
    """
    app.include_router(admin_router, prefix="/admin", tags=[module_name])


def register_admin_menu():
    """관리자 메뉴 등록
    """

    admin_menu = {
        f"{module_name}": [
            {
                "name": "플러그인 데모",
                "url": "",
                "permission": "",
            },
            {
                "id": module_name + "1",  # 메뉴 아이디
                "name": "데모 플러그인 메뉴1",
                "url": "test_demo_admin_template",
                "permission": "demo1",
            },
            {
                "id": module_name + "2",  # 메뉴 아이디
                "name": "데모 플러그인 메뉴2",
                "url": "test_demo_admin",
                "permission": "demo2",
            },
        ]
    }

    return admin_menu
