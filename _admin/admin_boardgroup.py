from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models 
from common import *
from dataclassform import BoardGroupForm

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals['generate_one_time_token'] = generate_one_time_token

@router.get("/boardgroup_list")
def boardgroup_list(request: Request, db: Session = Depends(get_db)):
    '''
    게시판그룹관리 목록
    '''
    request.session["menu_key"] = "300200"
    
    groups = db.query(models.Group).all()
    return templates.TemplateResponse("admin/boardgroup_list.html", {"request": request, "groups": groups})


@router.post("/boardgroup_list_update")
def boardgroup_list_update(
    request: Request, 
    db: Session = Depends(get_db),
    token: Optional[str] = Form(...),
    checks: Optional[List[int]] = Form(None, alias="chk[]"),
    gr_id: Optional[List[str]] = Form(None, alias="group_id[]"),
    gr_subject: Optional[List[str]] = Form(None, alias="gr_subject[]"),
    gr_admin: Optional[List[str]] = Form(None, alias="gr_admin[]"),
    gr_use_access: Optional[List[int]] = Form(None, alias="gr_use_access[]"),
    gr_order: Optional[List[int]] = Form(None, alias="gr_order[]"),
    ):
    
    if not token or not validate_one_time_token(token, 'update'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰값이 일치하지 않습니다."]})    

    # 선택수정
    for i in checks:
        print(gr_id[i])
        group = db.query(models.Group).filter(models.Group.gr_id == gr_id[i]).first()
        if group:
            group.gr_id = gr_id[i]
            group.gr_subject = gr_subject[i]
            group.gr_admin = gr_admin[i]
            group.gr_use_access = get_from_list(gr_use_access, i, 0)
            group.gr_order = gr_order[i]
            db.commit()

    query_string = generate_query_string(request)            
    
    return RedirectResponse(f"/admin/boardgroup_list?{query_string}", status_code=303)


@router.get("/boardgroup_form")
def boardgroup_form(request: Request, db: Session = Depends(get_db)):
    token = hash_password(hash_password("")) # 토큰값을 아무도 알수 없게 만듬
    request.session["token"] = token   
    
    return templates.TemplateResponse("admin/boardgroup_form.html", {"request": request, "group": None, "token": token})


@router.get("/boardgroup_form/{gr_id}")
def boardgroup_form(gr_id: str, request: Request, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
    if not group:
        raise HTTPException(status_code=404, detail=f"{gr_id} Group is not found.")

    # 토큰값을 게시판아이디로 만들어 세션에 저장하고 수정시 넘어오는 토큰값을 비교하여 수정 상태임을 확인
    token = hash_password(gr_id)
    request.session["token"] = token
    
    return templates.TemplateResponse("admin/boardgroup_form.html", {"request": request, "group": group, "token": token })


@router.post("/boardgroup_form_update")  
def boardgroup_form_update(request: Request, db: Session = Depends(get_db),
                        token : str = Form(...),
                        gr_id: str = Form(...),
                        form_data: BoardGroupForm = Depends(),
                        ):
    
    if validate_one_time_token(token, 'insert'):
        existing_group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
        if existing_group:
            errors = [f"{gr_id} 게시판그룹 아이디가 이미 존재합니다. (등록불가)"]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
        
        new_group = models.Group(gr_id=gr_id, **form_data.__dict__)
        db.add(new_group)
        db.commit()
        
    elif validate_one_time_token(token, 'update'):
        existing_group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
        if not existing_group:
            return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{gr_id} 게시판그룹 아이디가 존재하지 않습니다. (수정불가)"]})
        
        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_group, field, value)
        db.commit()
        
    else:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["잘못된 접근입니다."]})
        
    return RedirectResponse(url=f"/admin/boardgroup_form/{gr_id}", status_code=303)
