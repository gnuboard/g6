from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Path
from fastapi.responses import RedirectResponse

from bbs.social import SocialAuthService
from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import validate_token, validate_captcha
from lib.mail import send_password_reset_mail
from lib.member_lib import MemberService
from lib.pbkdf2 import create_hash

router = APIRouter()
templates = UserTemplates()
templates.env.globals["captcha_widget"] = captcha_widget


@router.get("/id_lost")
async def find_member_id_form(request: Request):
    """
    회원 ID 찾기 폼을 보여준다.
    """
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    context = {
        "request": request
    }
    return templates.TemplateResponse("/member/id_find_form.html", context)


@router.post("/id_lost",
             dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def find_member_id(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    mb_name: str = Form(...),
    mb_email: str = Form(...)
):
    """
    회원 ID 찾은 후 결과를 보여준다.
    """
    if request.state.login_member:
        return RedirectResponse("/", status_code=303)

    member_id, register_date = member_service.find_id(mb_name, mb_email)

    context = {
        "request": request,
        "member_id": member_id,
        "register_date": register_date
    }
    return templates.TemplateResponse(f"/member/id_find_result.html", context)


@router.get("/password_lost")
async def find_member_password_form(request: Request):
    """
    회원 비밀번호 찾기 폼을 보여준다.
    """
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    context = {
        "request": request,
    }
    return templates.TemplateResponse(
        f"/member/password_find_form.html", context)


@router.post("/password_lost",
             dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def find_member_password(
    request: Request,
    background_tasks: BackgroundTasks,
    member_service: Annotated[MemberService, Depends()],
    mb_id: str = Form(...),
    mb_email: str = Form(...),
):
    """
    회원정보를 찾은 후 비밀번호 재설정 링크 메일 발송
    """
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    member = member_service.find_member_from_password_info(mb_id, mb_email)
    # 비밀번호 재설정 메일 발송 처리(백그라운드)
    background_tasks.add_task(send_password_reset_mail, request, member)

    context = {
        "request": request,
        "member": member
    }
    return templates.TemplateResponse(f"/member/password_find_result.html", context)


@router.get("/password_reset/{mb_id}/{token}")
async def reset_password_form(
    request: Request,
    db: db_session,
    mb_id: str = Path(...),
    token: str = Path(...)
):
    """
    비밀번호 재설정 링크를 클릭한 후 비밀번호 재설정 폼을 보여준다.
    """
    config = request.state.config
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    member = db.scalar(
        select(Member).where(
            Member.mb_id == mb_id,
            Member.mb_lost_certify == token,
            Member.mb_id != config.cf_admin  # 최고관리자는 제외
        )
    )
    if not member:
        raise AlertException("유효하지 않은 요청입니다.", 403)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        raise AlertException("소셜로그인으로 가입하신 회원은 비밀번호를 재설정할 수 없습니다.", 400)

    # # 비밀번호 재설정 링크를 재사용 할 수 없도록 초기화
    # member.mb_lost_certify = ""
    # db.commit()

    context = {
        "request": request,
        "member": member
    }
    return templates.TemplateResponse(
        "/member/password_reset_form.html", context)


@router.post("/password_reset/{mb_id}/{token}",
             dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def reset_password(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    mb_id: str = Path(...),
    token: str = Path(...),
    mb_password: str = Form(..., min_length=4, max_length=20),
    mb_password_confirm: str = Form(..., min_length=4, max_length=20),
):
    """
    비밀번호를 재설정한다.
    """
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)
    if mb_password != mb_password_confirm:
        raise AlertException("비밀번호가 일치하지 않습니다.", 400)
    
    member_service.reset_password(mb_id, token, create_hash(mb_password))

    raise AlertException("비밀번호가 변경되었습니다.", 303, "/bbs/login")
