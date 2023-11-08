from dataclasses import dataclass

from fastapi import APIRouter, Form, UploadFile, File, Depends
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from common import *
from database import get_db
from dataclassform import MemberForm
from main import templates, app
from models import Member
from pbkdf2 import validate_password, create_hash

router = APIRouter()
templates.env.globals["captcha_widget"] = captcha_widget


@router.get("/member_confirm")
def check_member_form(request: Request):
    test_member = {"mb_id": ""}

    return templates.TemplateResponse(f"{request.state.device}/member/member_confirm.html", {
        "request": request,
        "member": test_member
    })


@dataclass
class FormData:
    mb_password: str = Form(...)


@router.post("/member_confirm", name='member_password')
def check_member(
        request: Request,
        form: FormData = Depends(),
        db: Session = Depends(get_db),
):
    errors = []
    mb_id = request.session.get("ss_mb_id", "")
    member = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
    else:
        if not validate_password(form.mb_password, member.mb_password):
            errors.append("아이디 또는 패스워드가 일치하지 않습니다.")

    if errors:
        return templates.TemplateResponse(f"{request.state.device}/member/member_confirm.html", {
            "request": request,
            "member": None,
            "errors": errors
        })

    return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)


@router.get("/member_profile/{mb_no}", name='member_profile')
def member_profile(request: Request, db: Session = Depends(get_db)):
    errors = []
    mb_id = request.session.get("ss_mb_id", "")
    if not mb_id:
        errors.append("로그인한 회원만 접근하실 수 있습니다.")
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

    member = db.query(Member).filter(Member.mb_id == mb_id).first()

    if not member:
        errors.append("회원정보가 없습니다.")
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

    config = request.state.config
    captcha = get_current_captcha_cls(captcha_name=config.cf_captcha)
    form_context = {
        "page": True,
        "action_url": app.url_path_for("member_profile", mb_no=request.path_params["mb_no"]),
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member, config) else "",
        "mb_icon_url": request.base_url.__str__() + f'data/member/{mb_id[:2]}/{mb_id}.gif?'
                       + f'{get_filetime_str(f"data/member/{mb_id[:2]}/{mb_id}.gif")}',

        "mb_img_url": request.base_url.__str__() + f'data/member_image/{mb_id[:2]}/{mb_id}.gif?'
                      + f'{get_filetime_str(f"data/member_image/{mb_id[:2]}/{mb_id}.gif")}',
    }

    return templates.TemplateResponse(f"{request.state.device}/member/register_form.html", {
        "config": request.state.config,
        "request": request,
        "member": member,
        "errors": errors,
        "form": form_context,
        "captcha": captcha.TEMPLATE_PATH if captcha is not None else '',
    })


@router.post("/member_profile/{mb_no}", name='member_profile_save')
async def member_profile_save(request: Request, db: Session = Depends(get_db),
                        token: str = Form(...),
                        mb_img: Optional[UploadFile] = File(None),
                        mb_icon: Optional[UploadFile] = File(None),
                        mb_password: str = Form(None),
                        mb_password_re: str = Form(None),
                        mb_certify_case: Optional[str] = Form(default=""),
                        mb_zip: str = Form(None),
                        member_form: MemberForm = Depends(MemberForm),
                        del_mb_img: str = Form(None),
                        del_mb_icon: str = Form(None),
                        recaptcha_response: Optional[str] = Form(alias="g-recaptcha-response", default=""),
                        ):
    errors = []
    if not validate_one_time_token(token, 'update'):
        errors.append("토큰이 유효하지 않습니다.")
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

    config = request.state.config
    captcha = get_current_captcha_cls(config.cf_captcha)
    if (captcha is not None) and (not await captcha.verify(config.cf_recaptcha_secret_key, recaptcha_response)):
        raise AlertException("캡차가 올바르지 않습니다.")

    mb_id = request.session.get("ss_mb_id", "")
    exists_member: Optional[Member] = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not exists_member:
        errors.append("회원정보가 없습니다.")
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

    # 한국 우편번호 (postalcode)
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
                errors.append("패스워드가 일치하지 않습니다.")
                return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
            is_password_changed = True

    # 이메일 변경
    if exists_member.mb_email != member_form.mb_email:
        if not member_form.mb_email:
            errors.append("이메일을 입력해 주세요.")

        elif not valid_email(member_form.mb_email):
            errors.append("이메일 양식이 올바르지 않습니다.")

        else:
            exists_email = db.query(Member.mb_email).filter(Member.mb_email == member_form.mb_email).first()
            if exists_email:
                errors.append("이미 존재하는 이메일 입니다.")

    # 닉네임변경 검사.
    is_nickname_changed = exists_member.mb_nick != member_form.mb_nick
    if is_nickname_changed:
        result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
        if result is not True:
            errors.append(result)

        if exists_member.mb_nick_date:
            result = validate_nickname_change_date(exists_member.mb_nick_date, config.cf_nick_modify)
            if result is not True:
                errors.append(result)

    member_image_path = f"data/member_image/{mb_id[:2]}/"
    member_icon_path = f"data/member/{mb_id[:2]}/"

    # 이미지 삭제
    if del_mb_img:
        delete_image(member_image_path, f"{mb_id}.gif")

    if del_mb_icon:
        delete_image(member_icon_path, f"{mb_id}.gif")

    if mb_img and mb_img.filename:
        if not re.match(r".*\.(jpg|jpeg|png|gif)$", mb_img.filename, re.IGNORECASE):
            errors.append("이미지 파일만 업로드 가능합니다.")

    # 이미지 검사
    if mb_icon and mb_icon.filename:
        mb_icon_info = Image.open(mb_icon.file)
        width, height = mb_icon_info.size

        if 0 < config.cf_member_icon_size < mb_icon.size:
            errors.append(f"아이콘 용량은 {config.cf_member_icon_size} 이하로 업로드 해주세요.")

        if config.cf_member_icon_width and config.cf_member_icon_height:
            if width > config.cf_member_icon_width or height > config.cf_member_icon_height:
                errors.append(f"아이콘 크기는 {config.cf_member_icon_width}x{config.cf_member_icon_height} 이하로 업로드 해주세요.")

        if not re.match(r".*\.(gif)$", mb_icon.filename, re.IGNORECASE):
            errors.append("gif 파일만 업로드 가능합니다.")

    if not member_form.mb_sex in {"m", "f"}:
        member_form.mb_sex = ""

    member_form.mb_level = exists_member.mb_level

    if errors:
        form_context = {
            "page": True,
            "action_url": app.url_path_for("member_profile", mb_no=request.path_params["mb_no"]),
            "name_readonly": "readonly",
            "hp_readonly": "readonly" if get_is_phone_certify(exists_member, config) else "",
            "mb_icon_url": request.base_url.__str__() + f'data/member/{mb_id[:2]}/{mb_id}.gif?'
                           + f'{get_filetime_str(f"data/member/{mb_id[:2]}/{mb_id}.gif")}',

            "mb_img_url": request.base_url.__str__() + f'data/member_image/{mb_id[:2]}/{mb_id}.gif?'
                          + f'{get_filetime_str(f"data/member_image/{mb_id[:2]}/{mb_id}.gif")}',
        }

        return templates.TemplateResponse("member/register_form.html", {
            "request": request, "errors": errors, "member": member_form, "config": config,
            "form": form_context,
        })

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
    return RedirectResponse(url="/", status_code=302)


def get_is_phone_certify(member: Member, config: Config) -> bool:
    """휴대폰 본인인증 사용여부 확인
    """
    return (config.cf_cert_use and config.cf_cert_req and
            (config.cf_cert_hp or config.cf_cert_simple) and
            member.mb_certify != "ipin")


def validate_nickname_change_date(before_nick_date: date, nick_modify_date) -> Union[str, bool]:
    """
        닉네임 변경 가능한지 날짜 검사
        Args:
            before_nick_date (datetime) : 이전 닉네임 변경한 날짜
            nick_modify_date (int) : 닉네임 수정가능일
        Raises:
            ValidationError: 닉네임 변경 가능일 안내
    """
    if nick_modify_date == 0:
        return True
    change_date = timedelta(days=nick_modify_date)

    if is_none_datetime(before_nick_date):
        before_nick_date = datetime.now().date()

    available_date = before_nick_date + change_date

    if datetime.now().date() < available_date:
        return f"{available_date.strftime('%Y-%m-%d')} 이후 닉네임을 변경할 수있습니다."

    return True


def validate_nickname(mb_nick: str, prohibit_id: str) -> Union[str, bool]:
    """ 등록가능한 닉네임인지 검사
    Args:
        mb_nick : 등록할 닉네임
        prohibit_id : 금지된 닉네임
    Return:
        가능한 닉네임이면 True 아니면 에러메시지 배열
    """
    if mb_nick is None or mb_nick.strip() == "":
        error_msg = "닉네임을 입력해주세요."
        return error_msg

    db = SessionLocal()
    result = db.query(Member.mb_nick).filter(Member.mb_nick == mb_nick).first()
    if result:
        error_msg = "해당 닉네임이 존재합니다."
        return error_msg

    if mb_nick in prohibit_id:
        error_msg = "닉네임으로 정할 수없는 단어입니다."
        return error_msg

    return True


def validate_userid(user_id: str, prohibit_id: str):
    """
    ID 로 사용 불가인 단어 검사
    Args:
        user_id (str): ID
        prohibit_id (str): 사용불가 아이디
    Raises:
        ValueError 정할 수없는 ID
    """

    if not user_id or user_id.strip() == "":
        error_msg = "ID를 입력해주세요."
        return error_msg

    if user_id in prohibit_id.strip():
        error_msg = "ID로 정할 수없는 단어입니다."
        return error_msg

    return True
