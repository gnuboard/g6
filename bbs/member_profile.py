from main import app

from fastapi import APIRouter, Form, File, Depends
from starlette.responses import RedirectResponse

from lib.common import *
from common.database import db_session
from common.formclass import MemberForm

from common.models import Member, MemberSocialProfiles
from lib.pbkdf2 import validate_password, create_hash

router = APIRouter()
templates = UserTemplates()
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals['getattr'] = getattr
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.globals["check_profile_open"] = check_profile_open


@router.get("/member_confirm")
async def check_member_form(request: Request, db: db_session):
    member = request.state.login_member
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 없습니다.")

    if request.state.config.cf_social_login_use:
        if db.query(MemberSocialProfiles.mb_id).filter(MemberSocialProfiles.mb_id == member.mb_id).first():
            request.session["ss_profile_change"] = True
            return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)

    return templates.TemplateResponse(f"{request.state.device}/member/member_confirm.html", {
        "request": request,
        "member": member
    })


@router.post("/member_confirm", name='member_password')
async def check_member(
        request: Request,
        mb_password: str = Form(...)
):
    member = request.state.login_member
    request.session["ss_profile_change"] = False
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 없습니다.")
    else:
        if not validate_password(mb_password, member.mb_password):
            raise AlertException(status_code=404, detail="아이디 또는 패스워드가 일치하지 않습니다.")

    request.session["ss_profile_change"] = True

    return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)


@router.get("/member_profile/{mb_no}", name='member_profile')
async def member_profile(request: Request, db: db_session):
    mb_id = request.session.get("ss_mb_id", "")
    if not mb_id:
        raise AlertException(status_code=403, detail="로그인한 회원만 접근하실 수 있습니다.")
    if not request.session.get("ss_profile_change", False):
        raise AlertException(status_code=403, detail="잘못된 접근입니다", url="/")

    member = db.query(Member).filter(Member.mb_id == mb_id).first()

    if not member:
        raise AlertException(status_code=404, detail="회원정보가 없습니다.")

    config = request.state.config
    form_context = {
        "page": True,
        "action_url": app.url_path_for("member_profile", mb_no=request.path_params["mb_no"]),
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member, config) else "",
        "mb_icon_url": request.base_url.__str__() + f'data/member/{mb_id[:2]}/{mb_id}.gif?'
                       + f'{get_filetime_str(f"data/member/{mb_id[:2]}/{mb_id}.gif")}',

        "mb_img_url": request.base_url.__str__() + f'data/member_image/{mb_id[:2]}/{mb_id}.gif?'
                      + f'{get_filetime_str(f"data/member_image/{mb_id[:2]}/{mb_id}.gif")}',
        "is_profile_open": check_profile_open(open_date=member.mb_open_date, config=request.state.config)
    }

    return templates.TemplateResponse(f"{request.state.device}/member/register_form.html", {
        "config": request.state.config,
        "request": request,
        "member": member,
        "form": form_context,
    })


@router.post("/member_profile/{mb_no}", name='member_profile_save', dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def member_profile_save(request: Request, db: db_session,
                              mb_img: Optional[UploadFile] = File(None),
                              mb_icon: Optional[UploadFile] = File(None),
                              mb_password: str = Form(None),
                              mb_password_re: str = Form(None),
                              mb_certify_case: Optional[str] = Form(default=""),
                              mb_zip: str = Form(None),
                              member_form: MemberForm = Depends(MemberForm),
                              del_mb_img: str = Form(None),
                              del_mb_icon: str = Form(None),
                              ):

    if not request.session.get("ss_profile_change", False):
        raise AlertException(status_code=403, detail="잘못된 접근입니다.", url=app.url_path_for("member_confirm"))

    mb_id = request.session.get("ss_mb_id", "")
    exists_member: Optional[Member] = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not exists_member:
        raise AlertException(status_code=403, detail="회원정보가 없습니다.")

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
                raise AlertException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
            is_password_changed = True

    # 이메일 변경
    if exists_member.mb_email != member_form.mb_email:
        if not member_form.mb_email:
            raise AlertException(status_code=400, detail="이메일을 입력해 주세요.")

        elif not valid_email(member_form.mb_email):
            raise AlertException(status_code=400, detail="이메일 양식이 올바르지 않습니다.")
        
        elif is_prohibit_email(request, member_form.mb_email):
            raise AlertException(f"{member_form.mb_email} 메일은 사용할 수 없습니다.", 400)

        else:
            exists_email = db.query(Member.mb_email).filter(Member.mb_email == member_form.mb_email).first()
            if exists_email:
                raise AlertException(status_code=400, detail="이미 존재하는 이메일 입니다.")

    # 닉네임변경 검사.
    is_nickname_changed = exists_member.mb_nick != member_form.mb_nick
    if is_nickname_changed:
        result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
        if result["msg"]:
            raise AlertException(status_code=400, detail=result["msg"])

        if exists_member.mb_nick_date:
            result = validate_nickname_change_date(exists_member.mb_nick_date, config.cf_nick_modify)
            if result["msg"]:
                raise AlertException(status_code=400, detail=result["msg"])

    member_image_path = f"data/member_image/{mb_id[:2]}/"
    member_icon_path = f"data/member/{mb_id[:2]}/"

    # 이미지 삭제
    if del_mb_img:
        delete_image(member_image_path, f"{mb_id}.gif")

    if del_mb_icon:
        delete_image(member_icon_path, f"{mb_id}.gif")

    if mb_img and mb_img.filename:
        if not re.match(r".*\.(gif)$", mb_img.filename, re.IGNORECASE):
            raise AlertException(status_code=400, detail="gif 파일만 업로드 가능합니다.")

    # 이미지 검사
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

    db.query(Member).filter(Member.mb_id == mb_id).update(member_form.__dict__)
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

    db = SessionLocal()
    result = db.query(Member.mb_nick).filter(Member.mb_nick == mb_nick).first()
    if result:
        message["msg"] = "해당 닉네임이 존재합니다."
        return message

    if mb_nick in prohibit_id:
        message["msg"] = "닉네임으로 정할 수없는 단어입니다."
        return message

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