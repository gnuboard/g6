from ..admin.admin_router import admin_router
from ..__init__ import module_name
from main import app

# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
app.include_router(admin_router, prefix="/admin", tags=[module_name])