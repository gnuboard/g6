from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from common import *
from database import get_db
import datetime
import models

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/register")
def get_register(request: Request, response: Response, db: Session = Depends(get_db)):
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # config = db.query(models.Config).first()
    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""
    return templates.TemplateResponse("bbs/register.html", request.state.context)

    # user = models.User(username=username)
    # db.add(user)
    # db.commit()
    # return {"username": username, "id": user.id}
    
@router.post("/register")
def post_register(request: Request, db: Session = Depends(get_db),
             agree: str = Form(...),
             agree2: str = Form(...),
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

@router.get("/register_form")
def get_register_form(request: Request, db: Session = Depends(get_db)):
    # 약관에 동의를 하지 않았다면
    agree = request.session.get("ss_agree", "")
    agree2 = request.session.get("ss_agree", "")
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)        
    return templates.TemplateResponse("bbs/register_form.html", {"request": request})
    
@router.post("/register_form")
def post_register_form(request: Request, db: Session = Depends(get_db),
                mb_id: str = Form(None),
                mb_password: str = Form(None),
                mb_password_re: str = Form(None),
                mb_name: str = Form(None),
                mb_nick: str = Form(None),
                mb_email: str = Form(None),
                ):
    agree = request.session.get("ss_agree", "")
    agree2 = request.session.get("ss_agree", "")
    if not agree:
        return RedirectResponse(url="/bbs/register", status_code=302)
    if not agree2:
        return RedirectResponse(url="/bbs/register", status_code=302)        
        
    errors = []
    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if member:
        errors.append("이미 존재하는 회원아이디 입니다.")
    if mb_password != mb_password_re:
        errors.append("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
    if not mb_name:
        errors.append("이름을 입력해 주세요.")
    if not mb_nick:
        errors.append("닉네임을 입력해 주세요.")
    if not mb_email:
        errors.append("이메일을 입력해 주세요.")
    else:
        exists_email = db.query(models.Member).filter(models.Member.mb_email == mb_email).first()
        if exists_email:
            errors.append("이미 존재하는 이메일 입니다.")
            
    register = {
        "agree": agree,
        "agree2": agree2,
        "mb_id": mb_id,
        "mb_name": mb_name,
        "mb_nick": mb_nick,
        "mb_email": mb_email,   
    }    
    if errors:
        return templates.TemplateResponse("bbs/register_form.html", {"request": request, "register": register, "errors": errors})
    
    # member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    # if member: 
    #     raise HTTPException(status_code=404, detail="{mb_id} is already exists.")
    
    member = models.Member(
        mb_id=mb_id, 
        mb_password=hash_password(mb_password), 
        mb_name=mb_name, 
        mb_nick=mb_nick,
        mb_nick_date=datetime.datetime.now(),
        mb_email=mb_email,
        mb_level=1,            
        mb_login_ip=request.client.host,
        mb_datetime=datetime.datetime.now(),
        mb_signature="",
        mb_today_login=datetime.datetime.now(),
        mb_email_certify=datetime.datetime.now(),
        mb_memo="",
        mb_lost_certify="",
        mb_open_date=datetime.datetime.now(),
        mb_profile="",
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
    if not mb_id:
        return RedirectResponse(url="/bbs/register", status_code=302)
    
    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not member:
        return RedirectResponse(url="/bbs/register", status_code=302)
    
    return templates.TemplateResponse("bbs/register_result.html", {"request": request, "member": member, "outlogin": request.state.context['outlogin']})

    
# @router.post("/register_form_update")  
# def config_form_update(request: Request, 
#                        db: Session = Depends(get_db),
#                        agree: str = Form(...),
#                        agree2: str = Form(...),
#                        mb_id: str = Form(...),
#                        mb_password: str = Form(...),
#                        mb_password_re: str = Form(...),
#                        mb_name: str = Form(...),
#                        mb_nick: str = Form(...),
#                        mb_email: str = Form(...),
#                        ):
    
    
    
#     member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
#     if member: 
#         raise HTTPException(status_code=404, detail="{mb_id} is already exists.")
    
#     member = models.Member(
#         mb_id=mb_id, 
#         mb_password=hash_password(mb_password), 
#         mb_name=mb_name, 
#         mb_nick=mb_nick,
#         mb_nick_date=datetime.datetime.now(),
#         mb_email=mb_email,
#         mb_level=1,            
#         mb_login_ip=request.client.host,
#         mb_datetime=datetime.datetime.now(),
#         mb_signature="",
#         mb_today_login=datetime.datetime.now(),
#         mb_email_certify=datetime.datetime.now(),
#         mb_memo="",
#         mb_lost_certify="",
#         mb_open_date=datetime.datetime.now(),
#         mb_profile="",
#     )
#     db.add(member)
#     db.commit()
#     # try:
#     #     member = models.Member(
#     #         mb_id=mb_id, 
#     #         mb_password=mb_password, 
#     #         mb_name=mb_name, 
#     #         mb_nick=mb_nick,
#     #         mb_nick_date=datetime.datetime.now(),
#     #         mb_email=mb_email,
#     #         mb_level=1,            
#     #         mb_login_ip=request.client.host,
#     #         mb_datetime=datetime.datetime.now(),
#     #     )
#     #     db.add(member)
#     #     db.commit()
#     # except IntegrityError:
#     #     db.rollback()
#     #     return templates.TemplateResponse("register_result.html", {"request": request, "member": None})
    
#     return templates.TemplateResponse("bbs/register_result.html", {"request": request, "member": member})

# @router.post("/post/")
# def create_post(title: str = Form(...), user_id: int = Form(...), db: Session = Depends(get_db)):
#     post = models.Post(title=title, user_id=user_id)
#     db.add(post)
#     db.commit()
#     return {"title": title, "user_id": user_id}

# @router.get("/{user_id}")
# def get_user(request: Request, user_id: int, db: Session = Depends(get_db)):
#     user = db.query(models.User).filter(models.User.id == user_id).first()
#     # return {"username": user.username, "posts": [{"title": post.title, "id": post.id} for post in user.posts]}
#     return templates.TemplateResponse("user.html", {"request": request, "user": user})

