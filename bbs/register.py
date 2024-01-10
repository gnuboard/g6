import secrets
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, File, Path, Query, UploadFile
from fastapi.responses import RedirectResponse, Response

from bbs.member_profile import (
    is_prohibit_email, validate_nickname, validate_userid
)
from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member
from core.template import UserTemplates
from lib.common import *
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
    agree: str = Form(...),
    agree2: str = Form(...)
):
    if not agree:
        raise AlertException(status_code=400, detail="회원가입약관에 동의해 주세요.")
    if not agree2:
        raise AlertException(status_code=400, detail="개인정보 수집 및 이용에 동의해 주세요.")

    request.session["ss_agree"] = agree
    request.session["ss_agree2"] = agree2
    return RedirectResponse(url="/bbs/register_form", status_code=302)


@router.get("/register_form", name='register_form')
async def get_register_form(request: Request):
    # 약관에 동의를 하지 않았다면
    agree = request.session.get("ss_agree", None)
    agree2 = request.session.get("ss_agree2", None)
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)

    config = request.state.config
    member = Member()
    member.mb_level = config.cf_register_level

    form_context = {
        # https 의 경우 http 경로가 넘어와서 제대로 전송이 되지 않음
        # "action_url": f"{request.base_url.__str__()}bbs{router.url_path_for('register_form_save')}",
        "agree": agree,
        "agree2": agree2,
        "is_profile_open": check_profile_open(open_date=None, config=request.state.config),
        "next_profile_open_date": get_next_profile_openable_date(open_date=None, config=request.state.config),
    }
    context = {
        "is_register": True,
        "request": request,
        "member": member,
        "form": form_context,
        "config": request.state.config,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/register_form",
             dependencies=[Depends(validate_token), Depends(validate_captcha)],
             name='register_form_save')
async def post_register_form(
    request: Request,
    db: db_session,
    mb_id: str = Form(None),
    mb_password: str = Form(None),
    mb_password_re: str = Form(None),
    mb_certify_case: str = Form(default=""),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
    mb_zip: str = Form(default=""),
    member_form: MemberForm = Depends()
):
    # 약관 동의 체크
    agree = request.session.get("ss_agree", "")
    agree2 = request.session.get("ss_agree", "")
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)

    config = request.state.config

    # 유효성 검사
    exists_member = db.scalar(select(Member).where(Member.mb_id == mb_id))
    if exists_member:
        raise AlertException(status_code=400, detail="이미 존재하는 회원아이디 입니다.")

    if not (mb_password and mb_password_re):
        raise AlertException(status_code=400, detail="비밀번호를 입력해 주세요.")

    elif mb_password != mb_password_re:
        raise AlertException(status_code=400, detail="비밀번호와 비밀번호 확인이 일치하지 않습니다.")

    if not member_form.mb_name:
        raise AlertException(status_code=400, detail="이름을 입력해 주세요.")
    if not member_form.mb_nick:
        raise AlertException(status_code=400, detail="닉네임을 입력해 주세요.")

    if config.cf_use_email_certify:
        if not member_form.mb_email:
            raise AlertException(status_code=400, detail="이메일을 입력해 주세요.")

        elif not valid_email(member_form.mb_email):
            raise AlertException(status_code=400, detail="이메일 양식이 올바르지 않습니다.")

        else:
            exists_email = db.scalar(
                exists(Member.mb_email)
                .where(Member.mb_email == member_form.mb_email).select()
            )
            if exists_email:
                raise AlertException(status_code=400, detail="이미 존재하는 이메일 입니다.")
    # 이메일 검사
    if is_prohibit_email(request, member_form.mb_email):
        raise AlertException(f"{member_form.mb_email} 메일은 사용할 수 없습니다.", 400)
    # 닉네임 검사
    result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
    if result["msg"]:
        raise AlertException(status_code=400, detail=result["msg"])
    # 회원 아이디 검사
    result = validate_userid(mb_id, config.cf_prohibit_id)
    if result["msg"]:
        raise AlertException(status_code=400, detail=result["msg"])

    if mb_certify_case and member_form.mb_certify:
        member_form.mb_certify = mb_certify_case
        member_form.mb_adult = member_form.mb_adult
    else:
        member_form.mb_certify = ""
        member_form.mb_adult = 0

    # 이미지 검사
    if mb_img and mb_img.filename:
        if not re.match(r".*\.(gif)$", mb_img.filename, re.IGNORECASE):
            raise AlertException(status_code=400, detail="gif 이미지 파일만 업로드 가능합니다.")

    if mb_icon and mb_icon.filename:
        mb_icon_info = Image.open(mb_icon.file)
        width, height = mb_icon_info.size

        if 0 < config.cf_member_icon_size < mb_icon.size:
            raise AlertException(status_code=400, detail=f"아이콘 용량은 {config.cf_member_icon_size} 이하로 업로드 해주세요.")

        if config.cf_member_icon_width and config.cf_member_icon_height:
            if width > config.cf_member_icon_width or height > config.cf_member_icon_height:
                raise AlertException(status_code=400,
                                     detail=f"아이콘 크기는 {config.cf_member_icon_width}x{config.cf_member_icon_height} 이하로 업로드 해주세요.")

        if not re.match(r".*\.(gif)$", mb_icon.filename, re.IGNORECASE):
            raise AlertException(status_code=400, detail="gif 파일만 업로드 가능합니다.")

    if member_form.mb_sex not in {"m", "f"}:
        member_form.mb_sex = ""

    # 한국 우편번호 (postalcode)
    if mb_zip:
        member_form.mb_zip1 = mb_zip[:3]
        member_form.mb_zip2 = mb_zip[3:]

    # 레벨 입력방지
    del member_form.mb_level

    # 유효성 검증 통과

    if mb_img and mb_img.filename:
        upload_file(
            mb_img,
            filename=mb_id + os.path.splitext(mb_img.filename)[1],
            path=os.path.join('data', 'member_image', f"{mb_id[:2]}")
        )

    if mb_icon and mb_icon.filename and mb_icon_info:
        # 파일객체를 pillow에서 열었으므로 따로 지정.
        path = os.path.join('data', 'member', f"{mb_id[:2]}")
        make_directory(path)
        filename = mb_id + os.path.splitext(mb_icon.filename)[1]
        mb_icon_info.save(os.path.join(path, filename))

    new_member = Member(mb_id=mb_id, **member_form.__dict__)
    new_member.mb_datetime = datetime.now()
    new_member.mb_password = create_hash(mb_password)
    new_member.mb_level = config.cf_register_level
    new_member.mb_login_ip = request.client.host
    new_member.mb_lost_certify = ""
    # DB 스키마 호환성을 위해 null 대신 최저년도를 사용.
    new_member.mb_nick_date = datetime(1, 1, 1, 0, 0, 0)
    new_member.mb_open_date = datetime(1, 1, 1, 0, 0, 0)
    new_member.mb_today_login = datetime.now()

    # 메일인증
    if config.cf_use_email_certify:
        # 일회용 인증키 생성
        new_member.mb_email_certify2 = secrets.token_hex(16)
    else:
        # 메일인증을 사용하지 않을 경우 바로 인증처리
        new_member.mb_email_certify = datetime.now()

    # 본인인증
    if mb_certify_case and member_form.mb_certify:
        new_member.mb_certify = mb_certify_case
        new_member.mb_adult = member_form.mb_adult
    else:
        new_member.mb_certify = ""
        new_member.mb_adult = 0

    db.add(new_member)
    db.commit()

    # 회원가입 포인트 지급
    insert_point(request, new_member.mb_id, config.cf_register_point,  "회원가입 축하", "@member", new_member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = member_form.mb_recommend
    if config.cf_use_recommend and mb_recommend:
        insert_point(request, mb_recommend, config.cf_recommend_point, f"{new_member.mb_id}의 추천인", "@member", mb_recommend, f"{new_member.mb_id} 추천")

    # 회원에게 인증메일 발송
    if config.cf_use_email_certify:
        subject = f"[{config.cf_title}] 회원가입 인증메일 발송"
        body = templates.TemplateResponse(
            "bbs/mail_form/register_certify_mail.html",
            {
                "request": request,
                "member": new_member,
                "certify_href": f"{request.base_url.__str__()}bbs/email_certify/{new_member.mb_id}?certify={new_member.mb_email_certify2}",
            }
        ).body.decode("utf-8")
        mailer(new_member.mb_email, subject, body)
    # 회원에게 회원가입 메일 발송
    elif config.cf_email_mb_member:
        subject = f"[{config.cf_title}] 회원가입을 축하드립니다."
        body = templates.TemplateResponse(
            "bbs/mail_form/register_send_member_mail.html",
            {
                "request": request,
                "member": new_member,
            }
        ).body.decode("utf-8")
        mailer(new_member.mb_email, subject, body)

    # 최고관리자에게 회원가입 메일 발송
    if config.cf_email_mb_super_admin:
        subject = f"[{config.cf_title}] {new_member.mb_nick} 님께서 회원으로 가입하셨습니다."
        body = templates.TemplateResponse(
            "bbs/mail_form/register_send_admin_mail.html",
            {
                "request": request,
                "member": new_member,
            }
        ).body.decode("utf-8")
        mailer(config.cf_admin_email, subject, body)

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