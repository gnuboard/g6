import sqlalchemy

from common.database import engine, DB_TABLE_PREFIX, SessionLocal
from main import app
from .. import models
from ..__init__ import module_name
from ..admin.admin_router import admin_router
from ..admin.num_book import admin_router as num_book_router
from ..admin.send import admin_router as send_router
from ..models import SmsBookGroup

# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
app.include_router(admin_router, prefix="/admin", tags=[module_name])
app.include_router(send_router, prefix="/admin", tags=[module_name])
app.include_router(num_book_router, prefix="/admin", tags=[module_name])

# table 유무로 install 체크
has_table = sqlalchemy.inspect(engine).has_table(DB_TABLE_PREFIX + "sms5_config")
if not has_table:
    models.Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        sms_book_group = SmsBookGroup()
        sms_book_group.bg_name = "미분류"
        db.add(sms_book_group)
        db.commit()
