from fastapi import APIRouter, Depends

from bbs.social import SocialAuthService
from common import *
from database import get_db
from main import templates

router = APIRouter()


@router.get("/member_leave")
def member_leave_form(request: Request):
    """
    회원탈퇴 폼을 보여준다.
    """

    member = request.state.login_member
    if not member:
        raise AlertException(status_code=400, detail="회원만 접근하실 수 있습니다.")

    return templates.TemplateResponse("member/member_confirm.html", {
        "request": request,
        "member": member,
        "token": generate_token(request, 'member_leave'),
    })


@router.post("/member_leave")
def member_leave(request: Request, db=Depends(get_db)):
    """회원탈퇴
    """
    if not compare_token(request, 'member_leave'):
        raise AlertException(status_code=400, detail="잘못된 접근입니다.")

    member = request.state.login_member
    if not member:
        raise AlertException(status_code=403, detail="회원만 접근하실 수 있습니다.")

    if request.state.is_super_admin:
        raise AlertException(status_code=400, detail="최고관리자는 탈퇴할 수 없습니다.")

    # 회원탈퇴
    leave_date = datetime.now().strftime("%Y-%m-%d")
    member.mb_leave_date = leave_date
    member.mb_memo = f"{member.mb_memo}\n{leave_date}탈퇴함"
    db.commit(member)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        SocialAuthService.unlink_social_login(member.mb_id)

    # 로그아웃
    request.session.clear()

    raise AlertException(status_code=200, detail=f"{member.mb_nick} 님께서는 {leave_date} 에 회원에서 탈퇴 하셨습니다.", url="/")
