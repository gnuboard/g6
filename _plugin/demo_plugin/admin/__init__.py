from _lib.plugin.service import register_admin
from ..admin.admin_router import admin_router
from ..__init__ import __plugin_id__
from main import app

# 플러그인의 admin 라우터를 등록한다. 
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
app.include_router(admin_router, prefix="/admin", tags=["demo_plugin"])

admin_menu = [
    {
        "name": "데모 플러그인 메뉴1",
        "url": "/demo_plugin",
        "permission": "demo1",
    },
    {
        "name": "데모 플러그인 메뉴2",
        "url": "/demo_plugin",
        "permission": "demo2",
    }
]

register_admin(admin_menu, __plugin_id__)
