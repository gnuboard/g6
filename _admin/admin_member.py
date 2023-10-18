from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from database import get_db
import models 
import datetime
from common import *
from dataclassform import MemberForm

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals['getattr'] = getattr
templates.env.globals['today'] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals['generate_one_time_token'] = generate_one_time_token

MEMBER_MENU_KEY = "200100"

@router.get("/member_list")
def member_list(request: Request, db: Session = Depends(get_db)):
    '''
    회원관리 목록
    '''
    request.session["menu_key"] = MEMBER_MENU_KEY
    
    members = db.query(models.Member).all()
    return templates.TemplateResponse("member_list.html", {"request": request, "members": members})


@router.get("/member_form")
def member_form_add(request: Request, db: Session = Depends(get_db)):
    '''
    회원추가 폼
    '''
    request.session["menu_key"] = MEMBER_MENU_KEY

    token = hash_password(hash_password("")) # 토큰값을 아무도 알수 없게 만듬
    request.session["token"] = token   
    
    return templates.TemplateResponse("member_form.html", {"request": request, "member": None, "token": token })


# 회원수정 폼
@router.get("/member_form/{mb_id}")
def member_form_edit(mb_id: str, request: Request, db: Session = Depends(get_db)):
    '''
    회원수정 폼
    '''
    request.session["menu_key"] = MEMBER_MENU_KEY
    
    sst = request.state.sst
    sod = request.state.sod
    sfl = request.state.sfl
    stx = request.state.stx
    page = request.state.page
    # print(request.state.sfl)
    
    request.session["menu_key"] = MEMBER_MENU_KEY


    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not member:
        raise HTTPException(status_code=404, detail=f"{mb_id} is not found.")

    # 토큰값을 회원아이디로 만들어 세션에 저장하고 수정시 넘어오는 토큰값을 비교하여 수정 상태임을 확인
    token = hash_password(mb_id)
    request.session["token"] = token
    
    return templates.TemplateResponse("member_form.html", {"request": request, "member": member, "token": token })

# DB등록 및 수정
@router.post("/member_form_update")
def member_form_update(
        request: Request, db: Session = Depends(get_db),
        token: str = Form(...),
        mb_id: str = Form(...),
        mb_certify_case: Optional[str] = Form(default=""),
        mb_password: Optional[str] = Form(...),
        form_data: MemberForm = Depends(),
        ):
    
    if validate_one_time_token(token, 'insert'):
        existing_member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
        if existing_member:
            errors = [f"{mb_id} 회원아이디가 이미 존재합니다. (등록불가)"]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

        request.state.time = datetime.now()
        new_member = models.Member(mb_id=mb_id, mb_password=mb_password, **form_data.__dict__)
        if mb_certify_case and form_data.mb_certify:
            new_member.mb_certify = mb_certify_case
            new_member.mb_adult = form_data.mb_adult
        else:
            new_member.mb_certify = ''
            new_member.mb_adult = 0

        if mb_password:
            new_member.mb_password = hash_password(mb_password)               
        else:
            # 비밀번호가 없다면 현재시간으로 해시값을 만든후 다시 해시 (알수없게 만드는게 목적)
            new_member.mb_password = hash_password(hash_password(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        new_member.mb_nick_date= request.state.time
        new_member.mb_datetime = request.state.time
        new_member.mb_today_login = request.state.time
        new_member.mb_open_date = request.state.time
        new_member.mb_email_certify = datetime(1, 1, 1, 0, 0)
        db.add(new_member)
        db.commit()
        
    elif validate_one_time_token(token, 'update'):
        existing_member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
        if not existing_member:
            errors = [f"{mb_id} 회원아이디가 존재하지 않습니다. (수정불가)"]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_member, field, value)
        
        # 비밀번호가 있다면 (수정했다면) : 수정에서는 비밀번호를 입력하지 않아도 됨 (선택사항)
        if mb_password:
            existing_member.mb_password = hash_password(mb_password)
        
        
        db.commit()
        
    else:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["잘못된 접근입니다."]})
        
    return RedirectResponse(url=f"/admin/member_form/{mb_id}", status_code=302)