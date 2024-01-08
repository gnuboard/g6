import re

from fastapi import APIRouter, Request
from sqlalchemy import select

from core.database import db_session
from core.models import Config, Login, Member
from core.template import UserTemplates

router = APIRouter()
templates = UserTemplates()


@router.get("/current_connect")
async def current_connect(
    request: Request,
    db: db_session
):
    """현재 접속중인 사용자의 정보를 반환합니다."""
    config: Config = request.state.config

    logins = db.execute(
        select(Login, Member)
        .outerjoin(Member, Login.mb_id == Member.mb_id)
        .where(Login.mb_id != config.cf_admin)
        .order_by(Login.lo_datetime.desc())
    ).all()

    for login, member in logins:
        if not request.state.is_super_admin:
            login.lo_ip = re.sub(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)",
                                 "\\1.#.#.\\4", login.lo_ip)
    context = {
        "request": request,
        "logins": logins,
    }
    return templates.TemplateResponse("/bbs/current_connect.html", context)
