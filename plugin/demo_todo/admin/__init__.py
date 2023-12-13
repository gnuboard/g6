from sqlalchemy import inspect

from common.database import engine, DB_TABLE_PREFIX
from .. import models
from ..admin.admin_router import admin_router
from ..plugin_info import module_name
from main import app

# install
if not inspect(engine).has_table(DB_TABLE_PREFIX + "todo"):
    models.Base.metadata.create_all(bind=engine)

# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
def register_admin_router():
    app.include_router(admin_router, prefix="/admin", tags=[module_name])


def register_admin_menu():
    admin_menu = {
        f"{module_name}": [
            {
                "name": "플러그인 데모",
                "url": "",
                "permission": ""
            },
            {
                "id": module_name + "1",  # 메뉴 아이디
                "name": "todo 추가",
                "url": "todo/create",
                "permission": "demo1"
            },
            {
                "id": module_name + "2",  # 메뉴 아이디
                "name": "todo 보기",
                "url": "todo/todos",
                "permission": "demo2"
            },
        ]
    }
    return admin_menu
