from fastapi import APIRouter, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from common import *
from database import get_db
from main import templates
from pbkdf2 import validate_password

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    """
    로그인 폼을 보여준다.
    """
    return templates.TemplateResponse("bbs/login_form.html", {"request": request})


@router.post("/login")
def login(request: Request, db: Session = Depends(get_db), mb_id: str = Form(...), mb_password: str = Form(...)):
    """
    로그인 폼화면에서 로그인
    """
    errors = []

    member = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not member:
        errors.append("회원정보가 존재하지 않습니다.")
    else:
        if not validate_password(password=mb_password, hash=member.mb_password):
            errors.append("아이디 또는 패스워드가 일치하지 않습니다.")

    if errors:
        return templates.TemplateResponse("bbs/login_form.html", {"request": request, "mb_id": mb_id, "errors": errors})

    # 로그인 성공시 세션에 저장
    request.session["ss_mb_id"] = member.mb_id
    # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
    request.session["ss_mb_key"] = session_member_key(request, member)

    return RedirectResponse(url="/", status_code=302)


@router.post("/login_check")
def check_login(request: Request, db: Session = Depends(get_db), mb_id: str = Form(...), mb_password: str = Form(...)):
    """
    outlogin 에서 로그인
    """
    errors = []
    member = db.query(Member).filter(Member.mb_id == mb_id).first()
    if not member:
        errors.append("회원정보가 존재하지 않습니다.")
    else:
        if not validate_password(mb_password, member.mb_password):
            errors.append("아이디 또는 패스워드가 일치하지 않습니다.")

    if errors:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

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
