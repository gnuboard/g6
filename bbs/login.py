from fastapi import APIRouter, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from common.common import *
from common.database import get_db

from common.pbkdf2 import validate_password

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR, extensions=["jinja2.ext.i18n"])
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_token"] = generate_token

@router.get("/login")
def login_form(request: Request,
               url: str = "/"):
    """
    로그인 폼을 보여준다.
    """
    context = {
        "request": request,
        "url": url
    }
    return templates.TemplateResponse("bbs/login_form.html", context)


@router.post("/login")
def login(request: Request, db: Session = Depends(get_db), 
        mb_id: str = Form(...), 
        mb_password: str = Form(...),
        url: str = Form(default="/")
    ):
    """
    로그인 폼화면에서 로그인
    """
    member = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 존재하지 않습니다.")
    else:
        if not validate_password(password=mb_password, hash=member.mb_password):
            raise AlertException(status_code=404, detail="아이디 또는 패스워드가 일치하지 않습니다.")

    # 로그인 성공시 세션에 저장
    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    request.session["ss_mb_key"] = session_member_key(request, member)

    return RedirectResponse(url=url, status_code=302)


@router.post("/login_check")
def check_login(request: Request, db: Session = Depends(get_db), mb_id: str = Form(...), mb_password: str = Form(...)):
    """
    outlogin 에서 로그인
    """
    member = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not member:
        raise AlertException(status_code=404, detail="회원정보가 존재하지 않습니다.")
    else:
        if not validate_password(password=mb_password, hash=member.mb_password):
            raise AlertException(status_code=404, detail="아이디 또는 패스워드가 일치하지 않습니다.")


    # 로그인 성공시 세션에 저장
    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    request.session["ss_mb_key"] = session_member_key(request, member)

    return RedirectResponse(url="/", status_code=302)


@router.get("/logout")
def logout(request: Request):
    """
    로그아웃, 세션을 초기화.
    """
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
