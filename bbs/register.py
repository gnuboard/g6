import secrets
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, File, Query, UploadFile
from fastapi.responses import RedirectResponse, Response

from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member
from core.template import UserTemplates
from lib.common import *
from lib.mail import send_register_mail
from lib.member_lib import (
    validate_and_update_member_image, validate_email, validate_mb_id, validate_nickname
)
from lib.dependencies import get_member, validate_token, validate_captcha
from lib.pbkdf2 import create_hash
from lib.point import insert_point
from lib.template_filters import default_if_none

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.globals["check_profile_open"] = check_profile_open


@router.get("/register")
async def get_register(
    request: Request,
    response: Response
):
    """
    회원가입 약관 동의 페이지
    """
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""

    context = {
        "request": request
    }
    return templates.TemplateResponse("/bbs/register.html", context)


@router.post("/register")
async def post_register(
    request: Request,
    agree: str = Form(None),
    agree2: str = Form(None)
):
    """
    회원가입 약관 동의 처리
    """
    if not agree:
        raise AlertException(status_code=400, detail="회원가입약관에 동의해 주세요.")
    if not agree2:
        raise AlertException(status_code=400, detail="개인정보 수집 및 이용에 동의해 주세요.")

    request.session["ss_agree"] = agree
    request.session["ss_agree2"] = agree2
    return RedirectResponse(url="/bbs/register_form", status_code=302)


@router.get("/register_form", name='register_form')
async def get_register_form(request: Request):
    """
    회원가입 폼 페이지
    """
    # 약관에 동의를 하지 않았다면
    if not request.session.get("ss_agree", None):
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not request.session.get("ss_agree2", None):
        return RedirectResponse(url="/bbs/register", status_code=302)

    config = request.state.config
    member = Member()
    member.mb_level = config.cf_register_level

    form_context = {
        # https 의 경우 http 경로가 넘어와서 제대로 전송이 되지 않음
        # "action_url": f"{request.base_url.__str__()}bbs{router.url_path_for('register_form_save')}",
        "is_profile_open": check_profile_open(open_date=None, config=config),
        "next_profile_open_date": get_next_profile_openable_date(open_date=None, config=config),
    }
    context = {
        "is_register": True,
        "request": request,
        "member": member,
        "form": form_context,
        "config": config,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/register_form",
             dependencies=[Depends(validate_token), Depends(validate_captcha)],
             name='register_form_save')
async def post_register_form(
    request: Request,
    db: db_session,
    background_tasks: BackgroundTasks,
    mb_id: str = Form(None),
    mb_password: str = Form(None),
    mb_password_re: str = Form(None),
    mb_certify_case: str = Form(default=""),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
    mb_zip: str = Form(default=""),
    member_form: MemberForm = Depends()
):
    """
    회원가입 처리
    """
    config = request.state.config

    # 약관 동의 체크
    if not request.session.get("ss_agree", None):
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not request.session.get("ss_agree2", None):
        return RedirectResponse(url="/bbs/register", status_code=302)

    # 회원 아이디 검사
    if len(mb_id) < 3 or len(mb_id) > 20:
        raise AlertException("회원아이디는 3~20자 이어야 합니다.", 400)
    if not re.match(r"^[a-zA-Z0-9_]+$", mb_id):
        raise AlertException("회원아이디는 영문자, 숫자, _ 만 사용할 수 있습니다.", 400)
    is_valid, message = validate_mb_id(request, mb_id)
    if not is_valid:
        raise AlertException(status_code=400, detail=message)

    # 비밀번호 검사
    if not (mb_password and mb_password_re):
        raise AlertException(status_code=400, detail="비밀번호를 입력해 주세요.")
    elif mb_password != mb_password_re:
        raise AlertException(status_code=400, detail="비밀번호와 비밀번호 확인이 일치하지 않습니다.")

    # 이름 검사
    if not member_form.mb_name:
        raise AlertException(status_code=400, detail="이름을 입력해 주세요.")

    # 닉네임 검사
    is_valid, message = validate_nickname(request, member_form.mb_nick)
    if not is_valid:
        raise AlertException(status_code=400, detail=message)

    # 이메일 검사
    is_valid, message = validate_email(request, member_form.mb_email)
    if not is_valid:
        raise AlertException(message, 400)

    # 본인인증
    if mb_certify_case and member_form.mb_certify:
        member_form.mb_certify = mb_certify_case
        member_form.mb_adult = member_form.mb_adult
    else:
        member_form.mb_certify = ""
        member_form.mb_adult = 0

    # 이미지 검사 & 업로드
    validate_and_update_member_image(request, mb_img, mb_icon, mb_id, None, None)

    if member_form.mb_sex not in {"m", "f"}:
        member_form.mb_sex = ""

    # 한국 우편번호 (postalcode)
    if mb_zip:
        member_form.mb_zip1 = mb_zip[:3]
        member_form.mb_zip2 = mb_zip[3:]

    # 레벨 입력방지
    del member_form.mb_level

    new_member = Member(mb_id=mb_id, **member_form.__dict__)
    new_member.mb_password = create_hash(mb_password)
    new_member.mb_level = config.cf_register_level
    new_member.mb_login_ip = get_client_ip(request)

    # 메일인증
    if config.cf_use_email_certify:
        # 일회용 인증키 생성
        new_member.mb_email_certify2 = secrets.token_hex(16)
    else:
        # 메일인증을 사용하지 않을 경우 바로 인증처리
        new_member.mb_email_certify = datetime.now()

    db.add(new_member)
    db.commit()

    # 회원가입 포인트 지급
    insert_point(request, new_member.mb_id, config.cf_register_point,  "회원가입 축하", "@member", new_member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = member_form.mb_recommend
    if config.cf_use_recommend and mb_recommend:
        insert_point(request, mb_recommend, config.cf_recommend_point, f"{new_member.mb_id}의 추천인", "@member", mb_recommend, f"{new_member.mb_id} 추천")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, new_member)

    # 회원가입 이후 세션 처리
    if not config.cf_use_email_certify:
        request.session["ss_mb_id"] = new_member.mb_id
        request.session["ss_mb_key"] = session_member_key(request, new_member)
    request.session["ss_mb_reg"] = new_member.mb_id

    return RedirectResponse(url="/bbs/register_result", status_code=302)


@router.get("/register_result")
async def register_result(
    request: Request,
    db: db_session
):
    """
    회원가입 결과 페이지
    """
    register_mb_id = request.session.get("ss_mb_reg", "")
    if "ss_mb_reg" in request.session:
        request.session.pop("ss_mb_reg")

    # 회원가입이 아닐때.
    if not register_mb_id:
        return RedirectResponse(url="/bbs/register", status_code=302)

    member = db.scalar(select(Member).where(Member.mb_id == register_mb_id))
    if not member:
        # 가입실패
        return RedirectResponse(url="/bbs/register", status_code=302)

    context = {
        "request": request,
        "member": member,
    }
    return templates.TemplateResponse("/bbs/register_result.html", context)


@router.get("/email_certify/{mb_id}")
async def email_certify(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_member)],
    certify: str = Query(...),
):
    """
    회원가입 메일인증 처리
    """
    if member.mb_leave_date or member.mb_intercept_date:
        raise AlertException("탈퇴한 회원이거나 차단된 회원입니다.", 403, "/")
    elif member.mb_email_certify != datetime(1, 1, 1, 0, 0, 0):
        raise AlertException("이미 인증된 회원입니다.", 403, "/")
    elif member.mb_email_certify2 != certify:
        raise AlertException("메일인증 요청 정보가 올바르지 않습니다.", 403, "/")

    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    raise AlertException(f"메일인증 처리를 완료 하였습니다. \\n\\n지금부터 {member.mb_id} 아이디로 로그인 가능합니다", 200, "/")