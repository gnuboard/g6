from datetime import datetime
from fastapi import APIRouter, Path
from starlette.requests import Request
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException
from core.models import Member
from lib.common import *
from main import templates

router = APIRouter()


@router.get('/profile/{member_id}')
async def get_profile(
    request: Request,
    db: db_session,
    member_id: str = Path(...),
):
    login_meber: Member = request.state.login_member
    if not login_meber:
        raise AlertException("회원만 이용하실 수 있습니다.", 403)
    
    member_profile: Member = db.scalar(select(Member).where(Member.mb_id == member_id))
    if not member_profile:
        raise AlertException("회원정보가 존재하지 않습니다.", 400)

    if not (request.state.is_super_admin or login_meber.mb_id == member_id):
        if not login_meber.mb_open:
            raise AlertException("자신의 정보를 공개하지 않으면 다른분의 정보를 조회할 수 없습니다.\\n\\n정보공개 설정은 회원정보수정에서 하실 수 있습니다.", 400)

        if not (member_profile.mb_open or request.state.is_super_admin):
            raise AlertException("정보공개를 하지 않았습니다.", 400)

    mb_datetime = member_profile.mb_datetime if not is_none_datetime(member_profile.mb_datetime) else datetime.now()
    member_after_regdate = (datetime.now() - mb_datetime).days + 1
    member_profile.mb_profile = member_profile.mb_profile if member_profile.mb_profile else "소개 내용이 없습니다."

    context = {
        "request": request,
        "member": member_profile,
        "reg_after_date": member_after_regdate
    }
    return templates.TemplateResponse("/member/member_profile.html", context)
