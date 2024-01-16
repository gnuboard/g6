from fastapi import APIRouter, Form, Query
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.common import *
from lib.member_lib import is_super_admin
from lib.pbkdf2 import validate_password
from lib.social import providers
from lib.social.social import SocialProvider, oauth

router = APIRouter()
templates = UserTemplates()


@router.get("/login")
async def login_form(
        request: Request,
        url: str = Query(default="/")
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
    if auto_login and not is_super_admin(request):
        age_1day = 60 * 60 * 24
        cookie_domain = request.state.cookie_domain
        response.set_cookie(key="ck_mb_id", value=member.mb_id,
                            max_age=age_1day * 30, domain=cookie_domain)
        response.set_cookie(key="ck_auto", value=ss_mb_key,
                            max_age=age_1day * 30, domain=cookie_domain)

    return response


@router.get("/logout")
async def logout(request: Request):
    """로그아웃 - 세션/자동로그인 쿠키를 초기화.
    Args:
        request (Request): request
    Returns:
        Response: RedirectResponse
    """
    if 'ss_social_access' in request.session:
        social_provider_name = request.session.get('ss_social_provider', None)
        if social_provider_name:
            provider_module_name = getattr(providers, f"{social_provider_name}")
            provider_class: SocialProvider = getattr(provider_module_name, f"{social_provider_name.capitalize()}")
            await provider_class.logout(oauth_instance=oauth, auth_token=request.session.get('ss_social_access'))

    request.session.clear()

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="ck_auto")
    response.delete_cookie(key="ck_mb_id")

    return response
