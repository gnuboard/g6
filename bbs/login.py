"""로그인/로그아웃 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.template import UserTemplates
from lib.common import session_member_key
from lib.member import is_super_admin
from lib.social import providers
from lib.social.social import SocialProvider, oauth
from service.member_service import MemberService

router = APIRouter(prefix="/bbs", tags=["login"], include_in_schema=False)
templates = UserTemplates()


@router.get("/login")
async def login_form(
        request: Request,
        url: str = Query(default="/")
):
    """로그인 폼을 보여준다."""
    context = {
        "request": request,
        "url": url
    }
    return templates.TemplateResponse("bbs/login_form.html", context)


@router.post("/login")
async def login(
        request: Request,
        member_service: Annotated[MemberService, Depends()],
        mb_id: str = Form(...),
        mb_password: str = Form(...),
        auto_login: bool = Form(default=False),
        url: str = Form(default="/")
):
    """로그인 폼화면에서 로그인"""
    member = member_service.authenticate_member(mb_id, mb_password)

    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    ss_mb_key = session_member_key(request, member)
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
    """
    로그아웃 
    - 세션/자동로그인 쿠키를 초기화.

    Args:
        request (Request): request

    Returns:
        Response: RedirectResponse
    """
    # 소셜로그인 연동 로그아웃
    if 'ss_social_access' in request.session:
        social_provider_name: str = request.session.get('ss_social_provider', None)
        if social_provider_name:
            provider_module_name = getattr(providers, f"{social_provider_name}")
            provider_class: SocialProvider = getattr(
                provider_module_name,
                f"{social_provider_name.capitalize()}"
            )

            await provider_class.logout(
                oauth_instance=oauth,
                auth_token=request.session.get('ss_social_access')
            )

    request.session.clear()

    response = RedirectResponse(url="/", status_code=302)
    if "ck_auto" in request.cookies:
        response.delete_cookie(key="ck_auto")
    if "ck_mb_id" in request.cookies:
        response.delete_cookie(key="ck_mb_id")

    return response
