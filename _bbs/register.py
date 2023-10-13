from dataclasses import dataclass

from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse, Response

from common import *
from database import get_db
from main import templates

router = APIRouter(prefix="/bbs")


@dataclass
class MemberForm(models.Member):
    mb_id: str = Form(None)
    mb_name: str = Form(...)
    mb_nick: str = Form(None)
    mb_email: str = Form(None)
    mb_birth: datetime = Form(None)
    mb_addr1: str = Form(None)
    mb_addr2: str = Form(None)
    mb_addr3: str = Form(None)
    mb_addr_jibeon: str = Form(None)
    mb_zip1: str = Form(None)
    mb_zip2: str = Form(None)
    mb_signature: str = Form(None)
    mb_profile: str = Form(None)
    mb_open: bool = Form(None)
    mb_sms: bool = Form(None)
    mb_mailling: bool = Form(None)
    mb_memo = Form(None)
    mb_hp: str = Form(None)
    mb_tel: str = Form(None)
    mb_homepage: str = Form(None)
    mb_sex: str = Form(None)
    mb_dupinfo: str = Form(None)
    mb_recommend: str = Form(None)
    mb_1: str = Form(None)
    mb_2: str = Form(None)
    mb_3: str = Form(None)
    mb_4: str = Form(None)
    mb_5: str = Form(None)
    mb_6: str = Form(None)
    mb_7: str = Form(None)
    mb_8: str = Form(None)
    mb_9: str = Form(None)
    mb_10: str = Form(None)

@router.get("/register")
def get_register(request: Request, response: Response, db: Session = Depends(get_db)):
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""
    return templates.TemplateResponse("bbs/register.html", request.state.context)


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

    form_context = {
        "action_url": router.url_path_for("register_form_save")
    }
    return templates.TemplateResponse(
        "member/register_form.html",
        {"request": request, "member": None, "form": form_context}
    )


@router.post("/register_form", name='register_form_save')
def post_register_form(request: Request, db: Session = Depends(get_db),
                       member_form: MemberForm = Depends(MemberForm),
                       mb_password: str = Form(None),
                       mb_password_re: str = Form(None),
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
    member = db.query(models.Member.mb_id).filter(models.Member.mb_id == member_form.mb_id).first()
    config = get_config()

    if member:
        errors.append("이미 존재하는 회원아이디 입니다.")
    if member_form.mb_password != mb_password_re:
        errors.append("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
    if not member_form.mb_name:
        errors.append("이름을 입력해 주세요.")
    if not member_form.mb_nick:
        errors.append("닉네임을 입력해 주세요.")
    if not member_form.mb_email:
        errors.append("이메일을 입력해 주세요.")
    else:
        exists_email = db.query(models.Member).filter(models.Member.mb_email == member_form.mb_email).first()
        if exists_email:
            errors.append("이미 존재하는 이메일 입니다.")

    form_context = {
        "agree": agree,
        "agree2": agree2,
        "name_readonly": "readonly" if (config.cf_cert_use and config.cf_cert_req) else ""
    }

    if errors:
        return templates.TemplateResponse("member/register_form.html",
                                          {"request": request, "form": form_context, "errors": errors})

    # if member: 
    #     raise HTTPException(status_code=404, detail="{mb_id} is already exists.")

    member = models.Member(
        mb_password=hash_password(mb_password),
        mb_nick_date=datetime.now(),
        mb_level=config.cf_register_level,
        mb_login_ip=request.client.host,
        mb_datetime=datetime.now(),
        mb_today_login=datetime.now(),
        mb_email_certify=datetime.now(),
        mb_memo="",
        mb_lost_certify="",
        mb_open_date=datetime.now(),
        mb_point=config.cf_register_point,
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
    mb_id = request.session.get("ss_mb_reg", "")
    if "ss_mb_reg" in request.session:
        request.session.pop("ss_mb_reg")

    if not mb_id:
        return RedirectResponse(url="/bbs/register", status_code=302)

    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not member:
        # 가입실패
        return RedirectResponse(url="/bbs/register", status_code=302)

    return templates.TemplateResponse("bbs/register_result.html", {
        "request": request, "member": member,
        "outlogin": request.state.context['outlogin']
    })
