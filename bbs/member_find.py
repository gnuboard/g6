import math
import secrets

from fastapi import APIRouter, Depends, Form, Path
from fastapi.responses import RedirectResponse

from bbs.social import SocialAuthService
from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import validate_token, validate_captcha
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


@router.post("/id_lost", dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def find_member_id(
    request: Request,
    db: db_session,
    mb_name: str = Form(...),
    mb_email: str = Form(...)
):
    """
    회원 ID 찾은 후 결과를 보여준다.
    """
    config = request.state.config
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    member = db.scalar(
        select(Member).where(
            Member.mb_name == mb_name,
            Member.mb_email == mb_email,
            Member.mb_id != config.cf_admin  # 최고관리자는 제외
        )
    )
    if not member:
        raise AlertException("입력하신 정보와 일치하는 회원이 없습니다.", 400)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        raise AlertException("소셜로그인으로 가입하신 회원은 아이디를 찾을 수 없습니다.", 400)

    context = {
        "request": request,
        "member_id": hide_member_id(member.mb_id),
        "register_date": member.mb_datetime.strftime("%Y-%m-%d %H:%M:%S")
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


@router.post("/password_lost", dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def find_member_password(
    request: Request,
    db: db_session,
    mb_id: str = Form(...),
    mb_email: str = Form(...),
):
    """
    회원정보를 찾은 후 비밀번호 재설정 링크 메일 발송
    """
    config = request.state.config
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    member = db.scalar(
        select(Member).where(
            Member.mb_id == mb_id,
            Member.mb_email == mb_email,
            Member.mb_id != config.cf_admin  # 최고관리자는 제외
        )
    )
    if not member:
        raise AlertException("입력하신 정보와 일치하는 회원이 없습니다.", 400)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        raise AlertException("소셜로그인으로 가입하신 회원은 비밀번호를 찾을 수 없습니다.", 400)

    # 비밀번호 재설정 링크 토큰 생성 및 저장
    member.mb_lost_certify = secrets.token_hex(16)
    db.commit()

    # 비밀번호 재설정 링크 메일 발송
    subject = f"[{config.cf_title}] 요청하신 비밀번호 찾기 메일입니다."
    body = templates.TemplateResponse(
        "bbs/mail_form/find_pasword_mail.html",
        {
            "request": request,
            "member": member,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    ).body.decode("utf-8")
    mailer(mb_email, subject, body)

    raise AlertException(f"{mb_email} 메일로 비밀번호를 변경할 수 있는 메일이 발송 되었습니다.\\n\\n메일을 확인하여 주십시오.", 303, "/")


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

    # 비밀번호 재설정 링크를 재사용 할 수 없도록 초기화
    member.mb_lost_certify = ""
    db.commit()

    context = {
        "request": request,
        "member": member
    }
    return templates.TemplateResponse(
        "/member/password_reset_form.html", context)


@router.post("/password_reset/{mb_id}", dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def reset_password(
    request: Request,
    db: db_session,
    mb_id: str = Path(...),
    mb_password: str = Form(..., min_length=4, max_length=20),
    mb_password_confirm: str = Form(..., min_length=4, max_length=20),
):
    """
    비밀번호를 재설정한다.
    """
    config = request.state.config
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=303)

    member = db.scalar(
        select(Member).where(
            Member.mb_id == mb_id,
            Member.mb_id != config.cf_admin  # 최고관리자는 제외
        )
    )
    if not member:
        raise AlertException("유효하지 않은 요청입니다.", 403)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        raise AlertException("소셜로그인으로 가입하신 회원은 비밀번호를 재설정할 수 없습니다.", 400)

    if mb_password != mb_password_confirm:
        raise AlertException("비밀번호가 일치하지 않습니다.", 400)

    # 비밀번호 변경
    member.mb_password = create_hash(mb_password)
    db.commit()

    raise AlertException("비밀번호가 변경되었습니다.", 303, "/bbs/login")


def hide_member_id(mb_id: str):
    """아이디를 가리기 위한 함수
    - 아이디의 절반을 가리고, 가려진 부분은 *로 표시한다.

    Args:
        mb_id (str): 회원 아이디

    Returns:
        str: 가려진 회원 아이디
    """
    id_len = len(mb_id)
    hide_len = math.floor(id_len / 2)
    start_len = math.ceil((id_len - hide_len) / 2)
    end_len = math.floor((id_len - hide_len) / 2)
    return mb_id[:start_len] + "*" * hide_len + mb_id[-end_len:]
