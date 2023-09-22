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
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select

@router.get("/board_list")
def board_list(request: Request, db: Session = Depends(get_db)):
    boards = db.query(models.Board).all()
    return templates.TemplateResponse("admin/board_list.html", {"request": request, "boards": boards})


@router.get("/board_form")
def board_form(request: Request, db: Session = Depends(get_db)):
    token = hash_password(hash_password("")) # 토큰값을 아무도 알수 없게 만듬
    request.session["token"] = token   
    
    context = {
        "request": request,
        "board": None,
        "token": token,
        "config": request.state.context['config']
    }
    return templates.TemplateResponse("admin/board_form.html", context)


@router.get("/board_form/{bo_table}")
def board_form(bo_table: str, request: Request, db: Session = Depends(get_db)):
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail=f"{bo_table} Board is not found.")

    # 토큰값을 게시판아이디로 만들어 세션에 저장하고 수정시 넘어오는 토큰값을 비교하여 수정 상태임을 확인
    token = hash_password(bo_table)
    request.session["token"] = token
    
    context = {
        "request": request,
        "board": board,
        "token": token,
        "config": request.state.context['config']
    }
    return templates.TemplateResponse("admin/board_form.html", context)


@router.post("/board_form_update")  
def board_form_update(request: Request, db: Session = Depends(get_db),
                        token: str = Form(...),
                        bo_table: str = Form(...),
                        gr_id: str = Form(...),
                        bo_subject: str = Form(...),
                        bo_mobile_subject: str = Form(None),
                        bo_device: str = Form(...),
                        bo_admin: str = Form(None),
                        bo_category_list: str = Form(None)
                        # bo_list_level: int = Form(...),
                        # bo_read_level: int = Form(...),
                        # bo_write_level: int = Form(...),
                        # bo_reply_level: int = Form(...),
                        # bo_comment_level: int = Form(...),
                        # bo_upload_level: int = Form(...),
                        # bo_download_level: int = Form(...),
                        # bo_html_level: int = Form(...),
                        # bo_link_level: int = Form(...),
                        # bo_count_delete: int = Form(...),
                        # bo_count_modify: int = Form(...),
                        # bo_read_point: int = Form(...),
                        # bo_write_point: int = Form(...),
                        # bo_comment_point: int = Form(...),
                        # bo_download_point: int = Form(...),
                        # bo_use_category: int = Form(...),
                        # bo_category_list: str = Form(...),
                        # bo_use_sideview: int = Form(...),
                        # bo_use_file_content: int = Form(...),
                        # bo_use_secret: int = Form(...),
                        # bo_use_dhtml_editor: int = Form(...),
                        # bo_select_editor: str = Form(...),
                        # bo_use_rss_view: int = Form(...),
                        # bo_use_good: int = Form(...),
                        # bo_use_nogood: int = Form(...),
                        # bo_use_name: int = Form(...),
                        # bo_use_signature: int = Form(...),
                        # bo_use_ip_view: int = Form(...),
                        # bo_use_list_view: int = Form(...),
                        # bo_use_list_file: int = Form(...),
                        # bo_use_list_content: int = Form(...),
                        # bo_table_width: int = Form(...),
                        # bo_subject_len: int = Form(...),
                        # bo_mobile_subject_len: int = Form(...),
                        # bo_page_rows: int = Form(...),
                        # bo_mobile_page_rows: int = Form(...),
                        # bo_new: int = Form(...),
                        # bo_hot: int = Form(...),
                        # bo_image_width: int = Form(...),
                        # bo_skin: str = Form(...),
                        # bo_mobile_skin: str = Form(...),
                        # bo_include_head: str = Form(...),
                        # bo_include_tail: str = Form(...),
                        # bo_content_head: str = Form(...),
                        # bo_mobile_content_head: str = Form(...),
                        # bo_content_tail: str = Form(...),
                        # bo_mobile_content_tail: str = Form(...),
                        # bo_insert_content: str = Form(...),
                        # bo_gallery_cols: int = Form(...),
                        # bo_gallery_width: int = Form(...),
                        # bo_gallery_height: int = Form(...),
                        # bo_mobile_gallery_width: int = Form(...),
                        # bo_mobile_gallery_height: int = Form(...),
                        # bo_upload_size: int = Form(...),
                        # bo_reply_order: int = Form(...),
                        # bo_use_search: int = Form(...),
                        # bo_order: int = Form(...),
                        # bo_count_write: int = Form(...),
                        # bo_count_comment: int = Form(...),
                        # bo_write_min: int = Form(...),
                        # bo_write_max: int = Form(...),
                        # bo_comment_min: int = Form(...),
                        # bo_comment_max: int = Form(...),
                        # bo_notice: str = Form(...),
                        # bo_upload_count: int = Form(...),
                        # bo_use_email: int = Form(...),
                        # bo_use_cert: str = Form(...),
                        # bo_use_sns: int = Form(...),
                        # bo_use_captcha: int = Form(...),
                        # bo_sort_field: str = Form(...),
                        # bo_1_subj: str = Form(...),
                        # bo_2_subj: str = Form(...),
                        # bo_3_subj: str = Form(...),
                        # bo_4_subj: str = Form(...),
                        # bo_5_subj: str = Form(...),
                        # bo_6_subj: str = Form(...),
                        # bo_7_subj: str = Form(...),
                        # bo_8_subj: str = Form(...),
                        # bo_9_subj: str = Form(...),
                        # bo_10_subj: str = Form(...),
                        # bo_1: str = Form(...),
                        # bo_2: str = Form(...),
                        # bo_3: str = Form(...),
                        # bo_4: str = Form(...),
                        # bo_5: str = Form(...),
                        # bo_6: str = Form(...),
                        # bo_7: str = Form(...),
                        # bo_8: str = Form(...),
                        # bo_9: str = Form(...),
                        # bo_10: str = Form(...),                       
                        ):
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if (board):
        board.gr_id = gr_id
        board.bo_subject = bo_subject
        board.bo_mobile_subject = bo_mobile_subject if bo_mobile_subject is not None else ""
        board.bo_device = bo_device
        board.bo_admin = bo_admin if bo_admin is not None else ""
        board.bo_category_list = bo_category_list if bo_category_list is not None else ""
        db.commit()
    else:
        board = models.Board(
            bo_table=bo_table,
            gr_id=gr_id,
            bo_subject=bo_subject if bo_subject is not None else "",
            bo_mobile_subject=bo_mobile_subject if bo_mobile_subject is not None else "",
            bo_device=bo_device,
            bo_admin=bo_admin if bo_admin is not None else "",
            bo_category_list=bo_category_list if bo_category_list is not None else "",
            # bo_list_level=bo_list_level,
            # bo_read_level=bo_read_level,
            # bo_write_level=bo_write_level,
            # bo_reply_level=bo_reply_level,
            # bo_comment_level=bo_comment_level,
            # bo_upload_level=bo_upload_level,
            # bo_download_level=bo_download_level,
            # bo_html_level=bo_html_level,
            # bo_link_level=bo_link_level,
            # bo_count_delete=bo_count_delete,
            # bo_count_modify=bo_count_modify,
            # bo_read_point=bo_read_point,
            # bo_write_point=bo_write_point,
            # bo_comment_point=bo_comment_point,
            # bo_download_point=bo_download_point,
            # bo_use_category=bo_use_category,
            # bo_category_list=bo_category_list,
            # bo_use_sideview=bo_use_sideview,
            # bo_use_file_content=bo_use_file_content,
            # bo_use_secret=bo_use_secret,
            # bo_use_dhtml_editor=bo_use_dhtml_editor,
            # bo_select_editor=bo_select_editor,
            # bo_use_rss_view=bo_use_rss_view,
            # bo_use_good=bo_use_good,
            # bo_use_nogood=bo_use_nogood,
            # bo_use_name=bo_use_name,
            # bo_use_signature=bo_use_signature,
            # bo_use_ip_view=bo_use_ip_view,
            # bo_use_list_view=bo_use_list_view,
            # bo_use_list_file=bo_use_list_file,
            # bo_use_list_content=bo_use_list_content,
            # bo_table_width=bo_table_width,
            # bo_subject_len=bo_subject_len,
            # bo_mobile_subject_len=bo_mobile_subject_len,
            # bo_page_rows=bo_page_rows,
            # bo_mobile_page_rows=bo_mobile_page_rows,
            # bo_new=bo_new,
            # bo_hot=bo_hot,
            # bo_image_width=bo_image_width,
            # bo_skin=bo_skin,
            # bo_mobile_skin=bo_mobile_skin,
            # bo_include_head=bo_include_head,
            # bo_include_tail=bo_include_tail,
            # bo_content_head=bo_content_head,
            # bo_mobile_content_head=bo_mobile_content_head,
            # bo_content_tail=bo_content_tail,
            # bo_mobile_content_tail=bo_mobile_content_tail,
            # bo_insert_content=bo_insert_content,
            # bo_gallery_cols=bo_gallery_cols,
            # bo_gallery_width=bo_gallery_width,
            # bo_gallery_height=bo_gallery_height,
            # bo_mobile_gallery_width=bo_mobile_gallery_width,
            # bo_mobile_gallery_height=bo_mobile_gallery_height,
            # bo_upload_size=bo_upload_size,
            # bo_reply_order=bo_reply_order,
            # bo_use_search=bo_use_search,
            # bo_order=bo_order,
            # bo_count_write=bo_count_write,
            # bo_count_comment=bo_count_comment,
            # bo_write_min=bo_write_min,
            # bo_write_max=bo_write_max,
            # bo_comment_min=bo_comment_min,
            # bo_comment_max=bo_comment_max,
            # bo_notice=bo_notice,
            # bo_upload_count=bo_upload_count,
            # bo_use_email=bo_use_email,
            # bo_use_cert=bo_use_cert,
            # bo_use_sns=bo_use_sns,
            # bo_use_captcha=bo_use_captcha,
            # bo_sort_field=bo_sort_field,
            # bo_1_subj=bo_1_subj,
            # bo_2_subj=bo_2_subj,
            # bo_3_subj=bo_3_subj,
            # bo_4_subj=bo_4_subj,
            # bo_5_subj=bo_5_subj,
            # bo_6_subj=bo_6_subj,
            # bo_7_subj=bo_7_subj,
            # bo_8_subj=bo_8_subj,
            # bo_9_subj=bo_9_subj,
            # bo_10_subj=bo_10_subj,
            # bo_1=bo_1,
            # bo_2=bo_2,
            # bo_3=bo_3,
            # bo_4=bo_4,
            # bo_5=bo_5,
            # bo_6=bo_6,
            # bo_7=bo_7,
            # bo_8=bo_8,
            # bo_9=bo_9,
            # bo_10=bo_10,
        )
        db.add(board)
        db.commit()
        
        # 새로운 게시판 테이블 생성
        # 지금 생성하지 않아도 자동으로 만들어짐
        # DynamicModel = dynamic_create_write_table(bo_table)
        
        # 처음 한번만 테이블을 생성한다.
        dynamic_create_write_table(bo_table, True)
        
        # DynamicModel = create_dynamic_create_write_table(f"g5_write_{bo_table}")

        # # 게시판 글, 댓글 테이블 생성
        # metadata = MetaData()
        
        # # src_table = models.Write.__table__        
        # # new_table = src_table.tometadata(metadata, f"{src_table}_{bo_table}")
        # # new_table.create(bind=db.bind)
        
        # src_table_name = models.Write.__table__
        # src_table = Table(src_table_name, metadata, autoload=engine)
        # new_table = Table(f"{src_table_name}_{bo_table}", metadata, *(column.copy() for column in src_table.columns))
        # new_table.create(engine)
        
        # with engine.begin() as conn:
        #     data = conn.execute(select([src_table])).fetchall()
        #     if data:
        #         conn.execute(new_table.insert(), data)
                
    return RedirectResponse("admin/board_list", status_code=303)
