from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session
from database import SessionLocal, get_db, engine
# from models import create_dynamic_create_write_table
import models 
from common import *
from jinja2 import Environment, FileSystemLoader
import random
import os
from typing import List, Optional
import socket

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected

@router.get("/boardgroup_list")
def boardgroup_list(request: Request, db: Session = Depends(get_db)):
    groups = db.query(models.Group).all()
    return templates.TemplateResponse("admin/boardgroup_list.html", {"request": request, "groups": groups})


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
                        gr_subject: str = Form(...),
                        gr_device: str = Form(None),
                        gr_admin: str = Form(None),
                        gr_use_access: int = Form(None),
                        gr_1_subj: str = Form(None),
                        gr_2_subj: str = Form(None),
                        gr_3_subj: str = Form(None),
                        gr_4_subj: str = Form(None),
                        gr_5_subj: str = Form(None),
                        gr_6_subj: str = Form(None),
                        gr_7_subj: str = Form(None),
                        gr_8_subj: str = Form(None),
                        gr_9_subj: str = Form(None),
                        gr_10_subj: str = Form(None),
                        gr_1: str = Form(None),
                        gr_2: str = Form(None),
                        gr_3: str = Form(None),
                        gr_4: str = Form(None),
                        gr_5: str = Form(None),
                        gr_6: str = Form(None),
                        gr_7: str = Form(None),
                        gr_8: str = Form(None),
                        gr_9: str = Form(None),
                        gr_10: str = Form(None),
                        ):

    # 세션에 저장된 토큰값과 입력된 토큰값이 다르다면 에러 (토큰 변조시 에러)
    # 토큰은 외부에서 접근하는 것을 막고 등록, 수정을 구분하는 용도로 사용
    ss_token = request.session.get("token", "")
    if not token or token != ss_token:
        raise HTTPException(status_code=403, detail="Invalid token.")

    # 수정의 경우 토큰값이 게시판그룹아이디로 만들어지므로 토큰값이 게시판그룹아이디와 다르다면 등록으로 처리 
    # 게시판그룹아이디 변조시에도 등록으로 처리
    if not verify_password(gr_id, token): # 등록
        
        chk_group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
        if chk_group:
            raise HTTPException(status_code=404, detail=f"{gr_id} : 게시판그룹 아이디가 이미 존재합니다.")
        
        group = models.Group(
            gr_id=gr_id,
            gr_subject=gr_subject,
            gr_device=gr_device if gr_device is not None else "",
            gr_admin=gr_admin if gr_admin is not None else "",
            gr_use_access=gr_use_access if gr_use_access is not None else 0,
            gr_1_subj=gr_1_subj if gr_1_subj is not None else "",
            gr_2_subj=gr_2_subj if gr_2_subj is not None else "",
            gr_3_subj=gr_3_subj if gr_3_subj is not None else "",
            gr_4_subj=gr_4_subj if gr_4_subj is not None else "",
            gr_5_subj=gr_5_subj if gr_5_subj is not None else "",
            gr_6_subj=gr_6_subj if gr_6_subj is not None else "",
            gr_7_subj=gr_7_subj if gr_7_subj is not None else "",
            gr_8_subj=gr_8_subj if gr_8_subj is not None else "",
            gr_9_subj=gr_9_subj if gr_9_subj is not None else "",
            gr_10_subj=gr_10_subj if gr_10_subj is not None else "",
            gr_1=gr_1 if gr_1 is not None else "",
            gr_2=gr_2 if gr_2 is not None else "",
            gr_3=gr_3 if gr_3 is not None else "",
            gr_4=gr_4 if gr_4 is not None else "",
            gr_5=gr_5 if gr_5 is not None else "",
            gr_6=gr_6 if gr_6 is not None else "",
            gr_7=gr_7 if gr_7 is not None else "",
            gr_8=gr_8 if gr_8 is not None else "",
            gr_9=gr_9 if gr_9 is not None else "",
            gr_10=gr_10 if gr_10 is not None else "",
        )
        db.add(group)
        db.commit()
    
    else: # 수정
        
        group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
        if not group:
            raise HTTPException(status_code=404, detail=f"{gr_id} : 게시판그룹 아이디가 존재하지 않습니다.")
        
        group.gr_subject = gr_subject
        group.gr_device = gr_device if gr_device is not None else ""
        group.gr_admin = gr_admin if gr_admin is not None else ""
        group.gr_use_access = gr_use_access if gr_use_access is not None else 0
        group.gr_1_subj = gr_1_subj if gr_1_subj is not None else ""
        group.gr_2_subj = gr_2_subj if gr_2_subj is not None else ""
        group.gr_3_subj = gr_3_subj if gr_3_subj is not None else ""
        group.gr_4_subj = gr_4_subj if gr_4_subj is not None else ""
        group.gr_5_subj = gr_5_subj if gr_5_subj is not None else ""
        group.gr_6_subj = gr_6_subj if gr_6_subj is not None else ""
        group.gr_7_subj = gr_7_subj if gr_7_subj is not None else ""
        group.gr_8_subj = gr_8_subj if gr_8_subj is not None else ""
        group.gr_9_subj = gr_9_subj if gr_9_subj is not None else ""
        group.gr_10_subj = gr_10_subj if gr_10_subj is not None else ""
        group.gr_1 = gr_1 if gr_1 is not None else ""
        group.gr_2 = gr_2 if gr_2 is not None else ""
        group.gr_3 = gr_3 if gr_3 is not None else ""
        group.gr_4 = gr_4 if gr_4 is not None else ""
        group.gr_5 = gr_5 if gr_5 is not None else ""
        group.gr_6 = gr_6 if gr_6 is not None else ""
        group.gr_7 = gr_7 if gr_7 is not None else ""
        group.gr_8 = gr_8 if gr_8 is not None else ""
        group.gr_9 = gr_9 if gr_9 is not None else ""
        group.gr_10 = gr_10 if gr_10 is not None else ""
        db.commit()
        
    return RedirectResponse(url=f"/admin/boardgroup_form/{gr_id}", status_code=303)
