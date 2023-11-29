from typing import List
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from common.database import get_db
import common.models as models 
from lib.common import *
from common.formclass import GroupForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = AdminTemplates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['number_format'] = number_format
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

@router.get("/boardgroup_list")
def boardgroup_list(request: Request, db: Session = Depends(get_db)):
    '''
    게시판그룹관리 목록
    '''
    sst = request.state.sst if request.state.sst else ""
    sod = request.state.sod
    sfl = request.state.sfl
    stx = request.state.stx
    sca = request.state.sca
    page = request.state.page
    request.session["menu_key"] = "300200"
    
    query = db.query(models.Group)
    if sst is not None and sst != "":
        if sod == "desc":
            query = query.order_by(desc(getattr(models.Group, sst)))
        else:
            query = query.order_by(asc(getattr(models.Group, sst)))
    if sfl is not None and stx is not None:
        if hasattr(models.Group, sfl):
            query = query.filter(getattr(models.Group, sfl).like(f"%{stx}%"))
    groups = query.all()
    
    # groups = db.query(models.Group).all()
    group_data = []

    for group in groups:
        # 그룹 테이블에서 원하는 필드 값을 가져와서 딕셔너리에 저장
        group_info = group.__dict__
        group_info.update({
            'board_count': db.query(models.Board).filter(models.Board.gr_id == group.gr_id).count(),
            # 접근회원수는 나중에 별도로 체크해야함
            'access_member_count': db.query(models.GroupMember).filter_by(gr_id = group.gr_id).count(),
        })
        group_data.append(group_info)
        
    return templates.TemplateResponse("boardgroup_list.html", {"request": request, "groups": group_data})


@router.post("/boardgroup_list_update")
def boardgroup_list_update(
    request: Request, 
    db: Session = Depends(get_db),
    token: str = Form(...),
    checks: List[int]= Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
    gr_subject: List[str] = Form(None, alias="gr_subject[]"),
    gr_admin: List[str] = Form(None, alias="gr_admin[]"),
    gr_use_access: List[int]= Form(None, alias="gr_use_access[]"),
    gr_order: List[int]= Form(None, alias="gr_order[]"),
    gr_device: List[str] = Form(None, alias="gr_device[]"),
):
    """게시판그룹 일괄 수정"""
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    # 선택수정
    for i in checks:
        group = db.query(models.Group).filter(models.Group.gr_id == gr_id[i]).first()
        if group:
            group.gr_id = gr_id[i]
            group.gr_subject = gr_subject[i]
            group.gr_admin = gr_admin[i]
            group.gr_use_access = get_from_list(gr_use_access, i, 0)
            group.gr_order = gr_order[i]
            group.gr_device = gr_device[i]
            db.commit()

    query_string = generate_query_string(request)            
    
    return RedirectResponse(f"/admin/boardgroup_list?{query_string}", status_code=303)


@router.post("/boardgroup_list_delete")
def boardgroup_list_delete(
    request: Request, 
    db: Session = Depends(get_db),
    token: str = Form(...),
    checks: List[int]= Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
):
    """게시판그룹 일괄 삭제"""
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    for i in checks:
        exists_board = db.query(models.Board).filter_by(gr_id = gr_id[i]).first()
        if not exists_board:
            db.query(models.Group).filter_by(gr_id = gr_id[i]).delete()
            db.query(models.GroupMember).filter_by(gr_id = gr_id[i]).delete()
        else:
            raise AlertException(f"{gr_id[i]} 게시판그룹에 속한 게시판이 존재합니다. (삭제불가)", 403)
    db.commit()
        
    return RedirectResponse(f"/admin/boardgroup_list?{request.query_params}", status_code=303)


@router.get("/boardgroup_form")
def boardgroup_form(request: Request, db: Session = Depends(get_db)):
    token = hash_password(hash_password("")) # 토큰값을 아무도 알수 없게 만듬
    request.session["token"] = token   
    
    return templates.TemplateResponse("boardgroup_form.html", {"request": request, "group": None, "token": token})


@router.get("/boardgroup_form/{gr_id}")
def boardgroup_form(gr_id: str, request: Request, db: Session = Depends(get_db)):
    group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
    if not group:
        raise HTTPException(status_code=404, detail=f"{gr_id} Group is not found.")

    member_count = db.query(models.GroupMember).filter_by(gr_id=gr_id).count()
    
    return templates.TemplateResponse("boardgroup_form.html", {"request": request, "group": group, "member_count": member_count })


@router.post("/boardgroup_form_update")  
def boardgroup_form_update(request: Request, db: Session = Depends(get_db),
                        action: str = Form(...),
                        token : str = Form(...),
                        gr_id: str = Form(...),
                        form_data: GroupForm = Depends(),
                        ):
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    if action == "w":
        existing_group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
        if existing_group:
            errors = [f"{gr_id} 게시판그룹 아이디가 이미 존재합니다. (등록불가)"]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
        
        new_group = models.Group(gr_id=gr_id, **form_data.__dict__)
        db.add(new_group)
        db.commit()
        
    elif action == "u":
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
