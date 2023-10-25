from fastapi import APIRouter, Form, File, UploadFile, Depends
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from _bbs.member_profile import validate_nickname, validate_userid
from common import *
from database import get_db
from dataclassform import MemberForm
from main import templates, app
from models import Member
from pbkdf2 import create_hash

router = APIRouter()


@router.get("/register")
def get_register(request: Request, response: Response, db: Session = Depends(get_db)):
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""
    return templates.TemplateResponse("bbs/register.html", {"request": request, "errors": ''})


@router.post("/register")
def post_register(request: Request, agree: str = Form(...), agree2: str = Form(...),
                  ):
    errors = []
    if not agree:
        errors.append("회원가입약관에 동의해 주세요.")
    if not agree2:
        errors.append("개인정보 수집 및 이용에 동의해 주세요.")
    if errors:
        return templates.TemplateResponse("bbs/register.html", {"request": request, "errors": errors})

    request.session["ss_agree"] = agree
    request.session["ss_agree2"] = agree2
    return RedirectResponse(url="/bbs/register_form", status_code=302)


@router.get("/register_form", name='register_form')
def get_register_form(request: Request):
    # 약관에 동의를 하지 않았다면
    agree = request.session.get("ss_agree", None)
    agree2 = request.session.get("ss_agree2", None)
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)

    member = Member()
    member.mb_level = 1

    form_context = {
        "action_url": app.url_path_for("register_form_save"),
        "agree": agree,
        "agree2": agree2,
    }

    return templates.TemplateResponse(
        "member/register_form.html",
        context={
            "is_register": True,
            "request": request,
            "member": member,
            "form": form_context,
            "errors": '',
            "config": request.state.config,
        }
    )


@router.post("/register_form", name='register_form_save')
async def post_register_form(request: Request, db: Session = Depends(get_db),
                             mb_id: str = Form(None),
                             mb_password: str = Form(None),
                             mb_password_re: str = Form(None),
                             mb_img: Optional[UploadFile] = File(None),
                             mb_icon: Optional[UploadFile] = File(None),
                             mb_zip: Optional[str] = Form(default=""),
                             member_form: MemberForm = Depends(),
                             ):
    # 약관 동의 체크
    agree = request.session.get("ss_agree", "")
    agree2 = request.session.get("ss_agree", "")
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)

    # 유효성 검사
    errors = []
    member = db.query(Member.mb_id, Member.mb_email).filter(Member.mb_id == mb_id).first()
    config = request.state.config

    if member:
        errors.append("이미 존재하는 회원아이디 입니다.")

    if not (mb_password and mb_password_re):
        errors.append("비밀번호를 입력해 주세요.")

    elif mb_password != mb_password_re:
        errors.append("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

    if not member_form.mb_name:
        errors.append("이름을 입력해 주세요.")
    if not member_form.mb_nick:
        errors.append("닉네임을 입력해 주세요.")

    if config.cf_use_email_certify:
        if not member_form.mb_email:
            errors.append("이메일을 입력해 주세요.")

        elif not valid_email(member_form.mb_email):
            errors.append("이메일 양식이 올바르지 않습니다.")

        else:
            exists_email = db.query(Member.mb_email).filter(Member.mb_email == member_form.mb_email).first()
            if exists_email:
                errors.append("이미 존재하는 이메일 입니다.")

    # 닉네임 검사
    result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
    if result is not True:
        errors.append(result)

    result = validate_userid(mb_id, config.cf_prohibit_id)
    if result is not True:
        errors.append(result)

    # 이미지 검사
    if mb_img and mb_img.filename:
        if not re.match(r".*\.(jpg|jpeg|png|gif)$", mb_img.filename, re.IGNORECASE):
            errors.append("이미지 파일만 업로드 가능합니다.")

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

    # 레벨 입력방지
    del member_form.mb_level

    # 유효성 검증 통과

    form_context = {
        "agree": agree,
        "agree2": agree2,
        "name_readonly": "readonly" if (config.cf_cert_use and config.cf_cert_req) else "",
        "mb_zip": mb_zip
    }

    if errors:
        return templates.TemplateResponse(
            "member/register_form.html",
            context={
                "request": request,
                "member": Member(mb_id=mb_id, mb_level=1, **member_form.__dict__),
                "is_register": True,
                "config": request.state.config,
                "form": form_context, "errors": errors
            })

    # 우편번호 (postalcode)
    member_form.mb_zip1 = mb_zip[:3]
    member_form.mb_zip2 = mb_zip[3:]

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

    member = Member(
        mb_id=mb_id,
        mb_datetime=datetime.now(),
        mb_email_certify=datetime(1, 1, 1, 0, 0),
        mb_password=create_hash(mb_password),
        mb_level=config.cf_register_level,
        mb_login_ip=request.client.host,
        mb_lost_certify="",
        mb_nick_date=datetime.now(),
        mb_open_date=datetime.now(),
        mb_point=config.cf_register_point,
        mb_today_login=datetime.now(),
        **member_form.__dict__
    )
    db.add(member)
    db.commit()

    request.session["ss_mb_id"] = member.mb_id
    request.session["ss_mb_key"] = session_member_key(request, member)
    request.session["ss_mb_reg"] = member.mb_id

    return RedirectResponse(url="/bbs/register_result", status_code=302)


@router.get("/register_result")
def register_result(request: Request, db: Session = Depends(get_db)):
    register_mb_id = request.session.get("ss_mb_reg", "")
    if "ss_mb_reg" in request.session:
        request.session.pop("ss_mb_reg")

    # 회원가입이 아닐때.
    if not register_mb_id:
        return RedirectResponse(url="/bbs/register", status_code=302)

    member = db.query(Member).filter(Member.mb_id == register_mb_id).first()
    if not member:
        # 가입실패
        return RedirectResponse(url="/bbs/register", status_code=302)

    return templates.TemplateResponse("bbs/register_result.html", {
        "request": request, "member": member,
    })
