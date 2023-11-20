from datetime import datetime

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from starlette.requests import Request

from common import AlertException, is_none_datetime
from database import get_db
from main import templates
from models import Member

router = APIRouter()


@router.get('/profile/{member_id}')
def get_profile(request: Request, member_id: str, db: Session = Depends(get_db)):
    print(request.state.login_member)
    if not request.state.login_member:
        raise AlertException("회원만 이용하실 수 있습니다.", 403)

    member_profile: Member = db.query(Member).filter(Member.mb_id == member_id).first()
    if not member_profile:
        raise AlertException("회원정보가 존재하지 않습니다.\\n\\n탈퇴하였을 수 있습니다.", 400)

    if not (member_profile.mb_open or request.state.is_super_admin):
        raise AlertException("정보공개를 하지 않았습니다.", 400)

    mb_datetime = member_profile.mb_datetime if not is_none_datetime(member_profile.mb_datetime) else datetime.now()
    member_after_regdate = (datetime.now() - mb_datetime).days + 1
    member_profile.mb_profile = member_profile.mb_profile if member_profile.mb_profile else "소개 내용이 없습니다."

    return templates.TemplateResponse(f"{request.state.device}/member/member_profile.html", {
        "request": request,
        "member": member_profile,
        "reg_after_date": member_after_regdate
    })
