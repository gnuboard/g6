from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse

from lib.common import *
from lib.pbkdf2 import validate_password
from core.database import db_session

router = APIRouter()
templates = UserTemplates()
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none


@router.get("/login")
async def login_form(
    request: Request,
    url: str = "/"
):
    """
    로그인 폼을 보여준다.
    """
    context = {
        "request": request,
        "url": url
    }
    return templates.TemplateResponse("bbs/login_form.html", context)


@router.post("/login")
async def login(
    request: Request,
    db: db_session,
    mb_id: str = Form(...),
    mb_password: str = Form(...),
    auto_login: bool = Form(default=False),
    url: str = Form(default="/")
):
    """
    로그인 폼화면에서 로그인
    """
    config = request.state.config

    member = db.scalar(select(Member).where(Member.mb_id == mb_id))
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 존재하지 않습니다.")
    elif not validate_password(password=mb_password, hash=member.mb_password):
        raise AlertException(status_code=404, detail="아이디 또는 패스워드가 일치하지 않습니다.")
    elif member.mb_leave_date or member.mb_intercept_date:
        raise AlertException("탈퇴 또는 차단된 회원입니다.", 404)
    elif config.cf_use_email_certify and member.mb_email_certify == datetime(1, 1, 1, 0, 0, 0):
        raise AlertException(f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다.", 404)

    ss_mb_key = session_member_key(request, member)
    # 로그인 성공시 세션에 저장
    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    request.session["ss_mb_key"] = ss_mb_key

    # 자동로그인
    response = RedirectResponse(url=url, status_code=302)
    # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
    if auto_login and not is_admin(request):
        response.set_cookie(key="ck_auto", value=ss_mb_key, max_age=60 * 60 * 24 * 30)
        response.set_cookie(key="ck_mb_id", value=member.mb_id, max_age=60 * 60 * 24 * 30)

    return response

@router.post("/login_check")
async def check_login(
    request: Request,
    db: db_session,
    mb_id: str = Form(...),
    mb_password: str = Form(...),
    auto_login: bool = Form(default=False),
    url: str = Form(default="/")
):
    """
    outlogin 에서 로그인
    """
    config = request.state.config

    member = db.scalar(select(Member).where(Member.mb_id == mb_id))
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 존재하지 않습니다.")
    elif not validate_password(password=mb_password, hash=member.mb_password):
        raise AlertException(status_code=404, detail="아이디 또는 패스워드가 일치하지 않습니다.")
    elif member.mb_leave_date or member.mb_intercept_date:
        raise AlertException("탈퇴 또는 차단된 회원입니다.", 404)
    elif config.cf_use_email_certify and member.mb_email_certify == datetime(1, 1, 1, 0, 0, 0):
        raise AlertException(f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다.", 404)

    ss_mb_key = session_member_key(request, member)
    # 로그인 성공시 세션에 저장
    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    request.session["ss_mb_key"] = ss_mb_key

    # 자동로그인
    response = RedirectResponse(url=url, status_code=302)
    # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
    if auto_login and not is_admin(request):
        response.set_cookie(key="ck_auto", value=ss_mb_key, max_age=60 * 60 * 24 * 30)
        response.set_cookie(key="ck_mb_id", value=member.mb_id, max_age=60 * 60 * 24 * 30)

    return response


@router.get("/logout")
async def logout(request: Request):
    """
    로그아웃
    - 세션/자동로그인 쿠키를 초기화.
    """
    request.session.clear()

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="ck_auto")
    response.delete_cookie(key="ck_mb_id")

    return response
