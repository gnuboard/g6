from typing import Dict
from typing_extensions import Annotated

from fastapi import APIRouter, Form, File, Depends, Path
from sqlalchemy import select, update
from starlette.responses import RedirectResponse


from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member, MemberSocialProfiles
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import (
    get_login_member, validate_token, validate_captcha
)
from lib.member_lib import (
    get_member_icon, get_member_image, validate_email, validate_nickname,
    validate_nickname_change_date, validate_and_update_member_image
)
from lib.pbkdf2 import validate_password, create_hash
from lib.template_filters import default_if_none

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.globals["check_profile_open"] = check_profile_open


@router.get("/member_confirm")
async def check_member_form(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)]
):
    """
    회원프로필 수정 전 비밀번호 확인 폼
    """
    # 회원정보를 수정할 수 있는지 확인하는 세션변수
    request.session["ss_profile_change"] = False

    # 소셜로그인 사용중이면 소셜로그인 정보가 있는지 확인
    if request.state.config.cf_social_login_use:
        social_member = db.scalar(
            select(MemberSocialProfiles).filter_by(mb_id=member.mb_id)
        )
        if social_member:
            request.session["ss_profile_change"] = True
            return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)

    context = {
        "request": request,
        "member": member,
        "action_url": request.url_for("member_password")
    }
    return templates.TemplateResponse("/member/member_confirm.html", context)


@router.post("/member_confirm", name='member_password')
async def check_member(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    mb_password: str = Form(...)
):
    """
    회원프로필 수정 전 비밀번호 확인 처리
    """
    if not validate_password(mb_password, member.mb_password):
        raise AlertException("아이디 또는 패스워드가 일치하지 않습니다.", 404)

    request.session["ss_profile_change"] = True

    return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)


@router.get("/member_profile/{mb_no}", name='member_profile')
async def member_profile(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    mb_no: int = Path(...),
):
    config = request.state.config

    if not request.session.get("ss_profile_change", False):
        raise AlertException("잘못된 접근입니다", 403, url="/")

    member = db.scalar(select(Member).filter_by(mb_id=member.mb_id))
    if not member:
        raise AlertException("회원정보가 없습니다.", 404)

    form_context = {
        "action_url": request.url_for("member_profile", mb_no=mb_no).path,
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member, config) else "",
        "mb_icon_url": get_member_icon(request, member.mb_id),
        "mb_img_url": get_member_image(request, member.mb_id),
        "is_profile_open": check_profile_open(open_date=member.mb_open_date, config=request.state.config)
    }

    context = {
        "config": request.state.config,
        "request": request,
        "member": member,
        "form": form_context,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/member_profile/{mb_no}", name='member_profile_save',
             dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def member_profile_save(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    mb_password: str = Form(None),
    mb_password_re: str = Form(None),
    mb_certify_case: str = Form(default=""),
    mb_zip: str = Form(None),
    member_form: MemberForm = Depends(MemberForm),
    del_mb_img: int = Form(None),
    del_mb_icon: int = Form(None),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
):
    """
    회원정보 수정 처리
    """
    if not request.session.get("ss_profile_change", False):
        raise AlertException("잘못된 접근입니다.", 403, url=request.url_for("member_password").path)

    mb_id = member.mb_id
    exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not exists_member:
        raise AlertException("회원정보가 없습니다.", 403)

    config = request.state.config

    # 한국 우편번호 (postalcode)
    if mb_zip:
        member_form.mb_zip1 = mb_zip[:3]
        member_form.mb_zip2 = mb_zip[3:]

    # 비밀번호 변경
    is_password_changed = False
    mb_password = mb_password.strip() if mb_password else ""
    mb_password_re = mb_password_re.strip() if mb_password_re else ""

    if mb_password and mb_password_re:
        # 비밀번호 변경 확인
        if not validate_password(password=mb_password, hash=exists_member.mb_password):
            if mb_password != mb_password_re:
                raise AlertException("비밀번호가 일치하지 않습니다.", 400)
            is_password_changed = True

    # 이메일 변경
    if exists_member.mb_email != member_form.mb_email:
        is_valid, message = validate_email(request, member_form.mb_email)
        if not is_valid:
            raise AlertException(message, 400)

    # 닉네임변경 검사
    if exists_member.mb_nick != member_form.mb_nick:
        is_valid, message = validate_nickname(request, member_form.mb_nick)
        if not is_valid:
            raise AlertException(message, 400)

        if exists_member.mb_nick_date:
            is_valid, message = validate_nickname_change_date(exists_member.mb_nick_date, config.cf_nick_modify)
            if not is_valid:
                raise AlertException(message, 400)

        member_form.mb_nick_date = datetime.now()

    # 이미지 검사 & 이미지 수정(삭제 포함)
    validate_and_update_member_image(request, mb_img, mb_icon, mb_id, del_mb_img, del_mb_icon)

    if not member_form.mb_sex in {"m", "f"}:
        member_form.mb_sex = ""

    member_form.mb_level = exists_member.mb_level


    del member_form.mb_birth
    del member_form.mb_name

    if is_password_changed:
        member_form.mb_password = create_hash(mb_password)

    # 본인인증
    if mb_certify_case and member_form.mb_certify:
        member_form.mb_certify = mb_certify_case
    else:
        member_form.mb_certify = ""
        member_form.mb_adult = 0

    if member_form.mb_open != exists_member.mb_open:
        member_form.mb_open_date = datetime.now()

    db.execute(
        update(Member).values(member_form.__dict__)
        .where(Member.mb_id == mb_id)
    )
    db.commit()

    if "ss_profile_change" in request.session:
        del request.session["ss_profile_change"]

    raise AlertException("회원정보가 수정되었습니다.", 302, "/")


def get_is_phone_certify(member: Member, config: Config) -> bool:
    """휴대폰 본인인증 사용여부 확인
    """
    return (config.cf_cert_use and config.cf_cert_req and
            (config.cf_cert_hp or config.cf_cert_simple) and
            member.mb_certify != "ipin")
