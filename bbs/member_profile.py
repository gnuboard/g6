from typing import Dict
from typing_extensions import Annotated

from fastapi import APIRouter, Form, File, Depends, Path
from sqlalchemy import select, update
from starlette.responses import RedirectResponse


from core.database import DBConnect, db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member, MemberSocialProfiles
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import (
    get_login_member, validate_token, validate_captcha
)
from lib.member_lib import get_member_icon, get_member_image
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
        "mb_icon_url": get_member_icon(member.mb_id),
        "mb_img_url": get_member_image(member.mb_id),
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
    del_mb_img: str = Form(None),
    del_mb_icon: str = Form(None),
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
        if not member_form.mb_email:
            raise AlertException("이메일을 입력해 주세요.", 400)

        elif not valid_email(member_form.mb_email):
            raise AlertException("이메일 양식이 올바르지 않습니다.", 400)

        elif is_prohibit_email(request, member_form.mb_email):
            raise AlertException(f"{member_form.mb_email} 메일은 사용할 수 없습니다.", 400)

        else:
            exists_email = db.scalar(
                exists(Member.mb_email)
                .where(Member.mb_email == member_form.mb_email).select()
            )
            if exists_email:
                raise AlertException("이미 존재하는 이메일 입니다.", 400)

    # 닉네임변경 검사.
    is_nickname_changed = exists_member.mb_nick != member_form.mb_nick
    if is_nickname_changed:
        result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
        if result["msg"]:
            raise AlertException(result["msg"], 400)

        if exists_member.mb_nick_date:
            result = validate_nickname_change_date(exists_member.mb_nick_date, config.cf_nick_modify)
            if result["msg"]:
                raise AlertException(result["msg"], 400)

    member_image_path = f"data/member_image/{mb_id[:2]}/"
    member_icon_path = f"data/member/{mb_id[:2]}/"

    # 이미지 삭제
    if del_mb_img:
        delete_image(member_image_path, f"{mb_id}.gif")

    if del_mb_icon:
        delete_image(member_icon_path, f"{mb_id}.gif")

    if mb_img and mb_img.filename:
        if not re.match(r".*\.(gif)$", mb_img.filename, re.IGNORECASE):
            raise AlertException("gif 파일만 업로드 가능합니다.", 400)

    # 이미지 검사
    if mb_icon and mb_icon.filename:
        mb_icon_info = Image.open(mb_icon.file)
        width, height = mb_icon_info.size

        if 0 < config.cf_member_icon_size < mb_icon.size:
            raise AlertException(f"아이콘 용량은 {config.cf_member_icon_size} 이하로 업로드 해주세요.", 400)

        if config.cf_member_icon_width and config.cf_member_icon_height:
            if width > config.cf_member_icon_width or height > config.cf_member_icon_height:
                raise AlertException(f"아이콘 크기는 {config.cf_member_icon_width}x{config.cf_member_icon_height} 이하로 업로드 해주세요.", 400)

        if not re.match(r".*\.(gif)$", mb_icon.filename, re.IGNORECASE):
            raise AlertException("gif 파일만 업로드 가능합니다.", 400)

    if not member_form.mb_sex in {"m", "f"}:
        member_form.mb_sex = ""

    member_form.mb_level = exists_member.mb_level

    # 유효성검사 통과
    if mb_img and mb_img.filename:
        upload_file(
            mb_img,
            filename=mb_id + os.path.splitext(mb_img.filename)[1],
            path=os.path.join('data', 'member_image', f"{mb_id[:2]}")
        )

    if mb_icon and mb_icon.filename and mb_icon_info:
        # 파일객체를 pillow에서 열었으므로 따로 지정.
        path = os.path.join('data', 'member', f"{mb_id[:2]}")
        os.makedirs(path, exist_ok=True)
        filename = mb_id + os.path.splitext(mb_icon.filename)[1]
        mb_icon_info.save(os.path.join(path, filename))

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

    db.execute(
        update(Member)
        .values(member_form.__dict__)
        .where(Member.mb_id == mb_id)
    )
    db.commit()
    if "ss_profile_change" in request.session:
        del request.session["ss_profile_change"]
    return RedirectResponse(url="/", status_code=302)


def get_is_phone_certify(member: Member, config: Config) -> bool:
    """휴대폰 본인인증 사용여부 확인
    """
    return (config.cf_cert_use and config.cf_cert_req and
            (config.cf_cert_hp or config.cf_cert_simple) and
            member.mb_certify != "ipin")


def validate_nickname_change_date(before_nick_date: date, nick_modify_date) -> Dict[str, str]:
    """
        닉네임 변경 가능한지 날짜 검사
        Args:
            before_nick_date (datetime) : 이전 닉네임 변경한 날짜
            nick_modify_date (int) : 닉네임 수정가능일
        Raises:
            ValidationError: 닉네임 변경 가능일 안내
    """
    message = {
        "msg": ""
    }
    if nick_modify_date == 0:
        return message
    change_date = timedelta(days=nick_modify_date)

    if is_none_datetime(before_nick_date):
        before_nick_date = datetime.now().date()

    available_date = before_nick_date + change_date

    if datetime.now().date() < available_date:
        message["msg"] = f"{available_date.strftime('%Y-%m-%d')} 이후 닉네임을 변경할 수있습니다."

    return message


def validate_nickname(mb_nick: str, prohibit_id: str) -> Dict[str, str]:
    """ 등록가능한 닉네임인지 검사
    Args:
        mb_nick : 등록할 닉네임
        prohibit_id : 금지된 닉네임
    Return:
        가능한 닉네임이면 True 아니면 에러메시지 배열
    """
    message = {
        "msg": ""
    }
    if mb_nick is None or mb_nick.strip() == "":
        message["msg"] = "닉네임을 입력해주세요."
        return message

    db = DBConnect().sessionLocal()
    result = db.scalar(select(Member).filter(Member.mb_nick == mb_nick))
    if result:
        message["msg"] = "해당 닉네임이 존재합니다."
        return message

    if mb_nick in prohibit_id:
        message["msg"] = "닉네임으로 정할 수없는 단어입니다."
        return message

    db.close()

    return message


def validate_userid(user_id: str, prohibit_id: str):
    """
    ID 로 사용 불가인 단어 검사
    Args:
        user_id (str): ID
        prohibit_id (str): 사용불가 아이디
    Raises:
        ValueError 정할 수없는 ID
    """
    message = {
        "msg": ""
    }
    if not user_id or user_id.strip() == "":
        message["msg"] = "ID를 입력해주세요."
        return message

    if user_id in prohibit_id.strip():
        message["msg"] = "ID로 정할 수없는 단어입니다."
        return message

    return message


def is_prohibit_email(request: Request, email: str):
    """금지된 메일인지 검사

    Args:
        request (Request): request 객체
        email (str): 이메일 주소

    Returns:
        bool: 금지된 메일이면 True, 아니면 False
    """
    config = request.state.config
    _, domain = email.split("@")

    # config에서 금지된 도메인 목록 가져오기
    cf_prohibit_email = getattr(config, "cf_prohibit_email", "")
    if cf_prohibit_email:
        prohibited_domains = [d.lower().strip() for d in cf_prohibit_email.split('\n')]

        # 주어진 도메인이 금지된 도메인 목록에 있는지 확인
        if domain.lower() in prohibited_domains:
            return True

    return False
