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
                        bo_category_list: str = Form(None),
                        bo_list_level: int = Form(None),
                        bo_read_level: int = Form(None),
                        bo_write_level: int = Form(None),
                        bo_reply_level: int = Form(None),
                        bo_comment_level: int = Form(None),
                        bo_upload_level: int = Form(None),
                        bo_download_level: int = Form(None),
                        bo_html_level: int = Form(None),
                        bo_link_level: int = Form(None),
                        bo_count_delete: int = Form(None),
                        bo_count_modify: int = Form(None),
                        bo_read_point: int = Form(None),
                        bo_write_point: int = Form(None),
                        bo_comment_point: int = Form(None),
                        bo_download_point: int = Form(None),
                        bo_use_category: int = Form(None),
                        bo_use_sideview: int = Form(None),
                        bo_use_file_content: int = Form(None),
                        bo_use_secret: int = Form(None),
                        bo_use_dhtml_editor: int = Form(None),
                        bo_select_editor: str = Form(None),
                        bo_use_rss_view: int = Form(None),
                        bo_use_good: int = Form(None),
                        bo_use_nogood: int = Form(None),
                        bo_use_name: int = Form(None),
                        bo_use_signature: int = Form(None),
                        bo_use_ip_view: int = Form(None),
                        bo_use_list_view: int = Form(None),
                        bo_use_list_file: int = Form(None),
                        bo_use_list_content: int = Form(None),
                        bo_table_width: int = Form(None),
                        bo_subject_len: int = Form(None),
                        bo_mobile_subject_len: int = Form(None),
                        bo_page_rows: int = Form(None),
                        bo_mobile_page_rows: int = Form(None),
                        bo_new: int = Form(None),
                        bo_hot: int = Form(None),
                        bo_image_width: int = Form(None),
                        bo_skin: str = Form(None),
                        bo_mobile_skin: str = Form(None),
                        bo_include_head: str = Form(None),
                        bo_include_tail: str = Form(None),
                        bo_content_head: str = Form(None),
                        bo_mobile_content_head: str = Form(None),
                        bo_content_tail: str = Form(None),
                        bo_mobile_content_tail: str = Form(None),
                        bo_insert_content: str = Form(None),
                        bo_gallery_cols: int = Form(None),
                        bo_gallery_width: int = Form(None),
                        bo_gallery_height: int = Form(None),
                        bo_mobile_gallery_width: int = Form(None),
                        bo_mobile_gallery_height: int = Form(None),
                        bo_upload_size: int = Form(None),
                        bo_reply_order: str = Form(None),
                        bo_use_search: int = Form(None),
                        bo_order: int = Form(None),
                        bo_count_write: int = Form(None),
                        bo_count_comment: int = Form(None),
                        bo_write_min: int = Form(None),
                        bo_write_max: int = Form(None),
                        bo_comment_min: int = Form(None),
                        bo_comment_max: int = Form(None),
                        bo_notice: int = Form(None),
                        bo_upload_count: int = Form(None),
                        bo_use_email: int = Form(None),
                        bo_use_cert: int = Form(None),
                        bo_use_sns: int = Form(None),
                        bo_use_captcha: int = Form(None),
                        bo_sort_field: str = Form(None),
                        bo_1_subj: str = Form(None),
                        bo_2_subj: str = Form(None),
                        bo_3_subj: str = Form(None),
                        bo_4_subj: str = Form(None),
                        bo_5_subj: str = Form(None),
                        bo_6_subj: str = Form(None),
                        bo_7_subj: str = Form(None),
                        bo_8_subj: str = Form(None),
                        bo_9_subj: str = Form(None),
                        bo_10_subj: str = Form(None),
                        bo_1: str = Form(None),
                        bo_2: str = Form(None),
                        bo_3: str = Form(None),
                        bo_4: str = Form(None),
                        bo_5: str = Form(None),
                        bo_6: str = Form(None),
                        bo_7: str = Form(None),
                        bo_8: str = Form(None),
                        bo_9: str = Form(None),
                        bo_10: str = Form(None),
                        ):

    # 세션에 저장된 토큰값과 입력된 토큰값이 다르다면 에러 (토큰 변조시 에러)
    # 토큰은 외부에서 접근하는 것을 막고 등록, 수정을 구분하는 용도로 사용
    ss_token = request.session.get("token", "")
    if not token or token != ss_token:
        raise HTTPException(status_code=403, detail="Invalid token.")

    # 수정의 경우 토큰값이 게시판아이디로 만들어지므로 토큰값이 게시판아이디와 다르다면 등록으로 처리
    # 게시판아이디 변조시에도 등록으로 처리
    if not verify_password(bo_table, token): # 등록

        chk_board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
        if chk_board:
            raise HTTPException(status_code=404, detail=f"{bo_table} : 게시판아이디가 이미 존재합니다.")

        board = models.Board(
            bo_table=bo_table,
            gr_id=gr_id,
            bo_subject=bo_subject if bo_subject is not None else "",
            bo_mobile_subject=bo_mobile_subject if bo_mobile_subject is not None else "",
            bo_device=bo_device,
            bo_admin=bo_admin if bo_admin is not None else "",
            bo_category_list=bo_category_list if bo_category_list is not None else "",
            bo_list_level=bo_list_level if bo_list_level is not None else 1,
            bo_read_level=bo_read_level if bo_read_level is not None else 1,
            bo_write_level=bo_write_level if bo_write_level is not None else 1,
            bo_reply_level=bo_reply_level if bo_reply_level is not None else 1,
            bo_comment_level=bo_comment_level if bo_comment_level is not None else 1,
            bo_upload_level=bo_upload_level if bo_upload_level is not None else 1,
            bo_download_level=bo_download_level if bo_download_level is not None else 1,
            bo_html_level=bo_html_level if bo_html_level is not None else 1,
            bo_link_level=bo_link_level if bo_link_level is not None else 1,
            bo_count_delete=bo_count_delete if bo_count_delete is not None else 0,
            bo_count_modify=bo_count_modify if bo_count_modify is not None else 0,
            bo_read_point=bo_read_point if bo_read_point is not None else 0,
            bo_write_point=bo_write_point if bo_write_point is not None else 0,
            bo_comment_point=bo_comment_point if bo_comment_point is not None else 0,
            bo_download_point=bo_download_point if bo_download_point is not None else 0,
            bo_use_category=bo_use_category if bo_use_category is not None else 0,
            bo_use_sideview=bo_use_sideview if bo_use_sideview is not None else 0,
            bo_use_file_content=bo_use_file_content if bo_use_file_content is not None else 0,
            bo_use_secret=bo_use_secret if bo_use_secret is not None else 0,
            bo_use_dhtml_editor=bo_use_dhtml_editor if bo_use_dhtml_editor is not None else 0,
            bo_select_editor=bo_select_editor if bo_select_editor is not None else "",
            bo_use_rss_view=bo_use_rss_view if bo_use_rss_view is not None else 0,
            bo_use_good=bo_use_good if bo_use_good is not None else 0,
            bo_use_nogood=bo_use_nogood if bo_use_nogood is not None else 0,
            bo_use_name=bo_use_name if bo_use_name is not None else 0,
            bo_use_signature=bo_use_signature if bo_use_signature is not None else 0,
            bo_use_ip_view=bo_use_ip_view if bo_use_ip_view is not None else 0,
            bo_use_list_view=bo_use_list_view if bo_use_list_view is not None else 0,
            bo_use_list_file=bo_use_list_file if bo_use_list_file is not None else 0,
            bo_use_list_content=bo_use_list_content if bo_use_list_content is not None else 0,
            bo_table_width=bo_table_width if bo_table_width is not None else 0,
            bo_subject_len=bo_subject_len if bo_subject_len is not None else 0,
            bo_mobile_subject_len=bo_mobile_subject_len if bo_mobile_subject_len is not None else 0,
            bo_page_rows=bo_page_rows if bo_page_rows is not None else 0,
            bo_mobile_page_rows=bo_mobile_page_rows if bo_mobile_page_rows is not None else 0,
            bo_new=bo_new if bo_new is not None else 0,
            bo_hot=bo_hot if bo_hot is not None else 0,
            bo_image_width=bo_image_width if bo_image_width is not None else 0,
            bo_skin=bo_skin if bo_skin is not None else "",
            bo_mobile_skin=bo_mobile_skin if bo_mobile_skin is not None else "",
            bo_include_head=bo_include_head if bo_include_head is not None else "",
            bo_include_tail=bo_include_tail if bo_include_tail is not None else "",
            bo_content_head=bo_content_head if bo_content_head is not None else "",
            bo_mobile_content_head=bo_mobile_content_head if bo_mobile_content_head is not None else "",
            bo_content_tail=bo_content_tail if bo_content_tail is not None else "",
            bo_mobile_content_tail=bo_mobile_content_tail if bo_mobile_content_tail is not None else "",
            bo_insert_content=bo_insert_content if bo_insert_content is not None else "",
            bo_gallery_cols=bo_gallery_cols if bo_gallery_cols is not None else 0,
            bo_gallery_width=bo_gallery_width if bo_gallery_width is not None else 0,
            bo_gallery_height=bo_gallery_height if bo_gallery_height is not None else 0,
            bo_mobile_gallery_width=bo_mobile_gallery_width if bo_mobile_gallery_width is not None else 0,
            bo_mobile_gallery_height=bo_mobile_gallery_height if bo_mobile_gallery_height is not None else 0,
            bo_upload_size=bo_upload_size if bo_upload_size is not None else 0,
            bo_reply_order=bo_reply_order if bo_reply_order is not None else "",
            bo_use_search=bo_use_search if bo_use_search is not None else 0,
            bo_order=bo_order if bo_order is not None else 0,
            bo_count_write=bo_count_write if bo_count_write is not None else 0,
            bo_count_comment=bo_count_comment if bo_count_comment is not None else 0,
            bo_write_min=bo_write_min if bo_write_min is not None else 0,
            bo_write_max=bo_write_max if bo_write_max is not None else 0,    
            bo_comment_min=bo_comment_min if bo_comment_min is not None else 0,
            bo_comment_max=bo_comment_max if bo_comment_max is not None else 0,
            bo_notice=bo_notice if bo_notice is not None else 0,
            bo_upload_count=bo_upload_count if bo_upload_count is not None else 0,
            bo_use_email=bo_use_email if bo_use_email is not None else 0,
            bo_use_cert=bo_use_cert if bo_use_cert is not None else 0,
            bo_use_sns=bo_use_sns if bo_use_sns is not None else 0,
            bo_use_captcha=bo_use_captcha if bo_use_captcha is not None else 0,
            bo_sort_field=bo_sort_field if bo_sort_field is not None else "",
            bo_1_subj=bo_1_subj if bo_1_subj is not None else "",
            bo_2_subj=bo_2_subj if bo_2_subj is not None else "",
            bo_3_subj=bo_3_subj if bo_3_subj is not None else "",
            bo_4_subj=bo_4_subj if bo_4_subj is not None else "",
            bo_5_subj=bo_5_subj if bo_5_subj is not None else "",
            bo_6_subj=bo_6_subj if bo_6_subj is not None else "",
            bo_7_subj=bo_7_subj if bo_7_subj is not None else "",
            bo_8_subj=bo_8_subj if bo_8_subj is not None else "",
            bo_9_subj=bo_9_subj if bo_9_subj is not None else "",
            bo_10_subj=bo_10_subj if bo_10_subj is not None else "",
            bo_1=bo_1 if bo_1 is not None else "",
            bo_2=bo_2 if bo_2 is not None else "",
            bo_3=bo_3 if bo_3 is not None else "",
            bo_4=bo_4 if bo_4 is not None else "",
            bo_5=bo_5 if bo_5 is not None else "",
            bo_6=bo_6 if bo_6 is not None else "",
            bo_7=bo_7 if bo_7 is not None else "",
            bo_8=bo_8 if bo_8 is not None else "",
            bo_9=bo_9 if bo_9 is not None else "",
            bo_10=bo_10 if bo_10 is not None else "",
        )
        db.add(board)
        db.commit()
        
    else: # 수정
        
        board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
        if not board:
            raise HTTPException(status_code=404, detail=f"{bo_table} : 게시판아이디가 존재하지 않습니다.")
    
        board.gr_id = gr_id
        board.bo_subject = bo_subject
        board.bo_mobile_subject = bo_mobile_subject if bo_mobile_subject is not None else ""
        board.bo_device = bo_device
        board.bo_admin = bo_admin if bo_admin is not None else ""
        board.bo_category_list = bo_category_list if bo_category_list is not None else ""
        board.bo_list_level = bo_list_level if bo_list_level is not None else 1
        board.bo_read_level = bo_read_level if bo_read_level is not None else 1
        board.bo_write_level = bo_write_level if bo_write_level is not None else 1
        board.bo_reply_level = bo_reply_level if bo_reply_level is not None else 1
        board.bo_comment_level = bo_comment_level if bo_comment_level is not None else 1
        board.bo_upload_level = bo_upload_level if bo_upload_level is not None else 1
        board.bo_download_level = bo_download_level if bo_download_level is not None else 1
        board.bo_html_level = bo_html_level if bo_html_level is not None else 1
        board.bo_link_level = bo_link_level if bo_link_level is not None else 1             
        board.bo_count_delete = bo_count_delete if bo_count_delete is not None else 0
        board.bo_count_modify = bo_count_modify if bo_count_modify is not None else 0
        board.bo_read_point = bo_read_point if bo_read_point is not None else 0
        board.bo_write_point = bo_write_point if bo_write_point is not None else 0
        board.bo_comment_point = bo_comment_point if bo_comment_point is not None else 0
        board.bo_download_point = bo_download_point if bo_download_point is not None else 0
        board.bo_use_category = bo_use_category if bo_use_category is not None else 0
        board.bo_use_sideview = bo_use_sideview if bo_use_sideview is not None else 0
        board.bo_use_file_content = bo_use_file_content if bo_use_file_content is not None else 0
        board.bo_use_secret = bo_use_secret if bo_use_secret is not None else 0
        board.bo_use_dhtml_editor = bo_use_dhtml_editor if bo_use_dhtml_editor is not None else 0
        board.bo_select_editor = bo_select_editor if bo_select_editor is not None else ""
        board.bo_use_rss_view = bo_use_rss_view if bo_use_rss_view is not None else 0
        board.bo_use_good = bo_use_good if bo_use_good is not None else 0
        board.bo_use_nogood = bo_use_nogood if bo_use_nogood is not None else 0
        board.bo_use_name = bo_use_name if bo_use_name is not None else 0
        board.bo_use_signature = bo_use_signature if bo_use_signature is not None else 0
        board.bo_use_ip_view = bo_use_ip_view if bo_use_ip_view is not None else 0
        board.bo_use_list_view = bo_use_list_view if bo_use_list_view is not None else 0
        board.bo_use_list_file = bo_use_list_file if bo_use_list_file is not None else 0
        board.bo_use_list_content = bo_use_list_content if bo_use_list_content is not None else 0
        board.bo_table_width = bo_table_width if bo_table_width is not None else 0
        board.bo_subject_len = bo_subject_len if bo_subject_len is not None else 0
        board.bo_mobile_subject_len = bo_mobile_subject_len if bo_mobile_subject_len is not None else 0
        board.bo_page_rows = bo_page_rows if bo_page_rows is not None else 0
        board.bo_mobile_page_rows = bo_mobile_page_rows if bo_mobile_page_rows is not None else 0
        board.bo_new = bo_new if bo_new is not None else 0
        board.bo_hot = bo_hot if bo_hot is not None else 0
        board.bo_image_width = bo_image_width if bo_image_width is not None else 0
        board.bo_skin = bo_skin if bo_skin is not None else ""
        board.bo_mobile_skin = bo_mobile_skin if bo_mobile_skin is not None else ""
        board.bo_include_head = bo_include_head if bo_include_head is not None else ""
        board.bo_include_tail = bo_include_tail if bo_include_tail is not None else ""
        board.bo_content_head = bo_content_head if bo_content_head is not None else ""
        board.bo_mobile_content_head = bo_mobile_content_head if bo_mobile_content_head is not None else ""
        board.bo_content_tail = bo_content_tail if bo_content_tail is not None else ""
        board.bo_mobile_content_tail = bo_mobile_content_tail if bo_mobile_content_tail is not None else ""
        board.bo_insert_content = bo_insert_content if bo_insert_content is not None else ""
        board.bo_gallery_cols = bo_gallery_cols if bo_gallery_cols is not None else 0
        board.bo_gallery_width = bo_gallery_width if bo_gallery_width is not None else 0
        board.bo_gallery_height = bo_gallery_height if bo_gallery_height is not None else 0
        board.bo_mobile_gallery_width = bo_mobile_gallery_width if bo_mobile_gallery_width is not None else 0
        board.bo_mobile_gallery_height = bo_mobile_gallery_height if bo_mobile_gallery_height is not None else 0
        board.bo_upload_size = bo_upload_size if bo_upload_size is not None else 0
        board.bo_reply_order = bo_reply_order if bo_reply_order is not None else ""
        board.bo_use_search = bo_use_search if bo_use_search is not None else 0
        board.bo_order = bo_order if bo_order is not None else 0
        board.bo_count_write = bo_count_write if bo_count_write is not None else 0
        board.bo_count_comment = bo_count_comment if bo_count_comment is not None else 0
        board.bo_write_min = bo_write_min if bo_write_min is not None else 0
        board.bo_write_max = bo_write_max if bo_write_max is not None else 0
        board.bo_comment_min = bo_comment_min if bo_comment_min is not None else 0
        board.bo_comment_max = bo_comment_max if bo_comment_max is not None else 0
        board.bo_notice = bo_notice if bo_notice is not None else 0
        board.bo_upload_count = bo_upload_count if bo_upload_count is not None else 0
        board.bo_use_email = bo_use_email if bo_use_email is not None else 0
        board.bo_use_cert = bo_use_cert if bo_use_cert is not None else ""
        board.bo_use_sns = bo_use_sns if bo_use_sns is not None else 0
        board.bo_use_captcha = bo_use_captcha if bo_use_captcha is not None else 0
        board.bo_sort_field = bo_sort_field if bo_sort_field is not None else ""
        board.bo_1_subj = bo_1_subj if bo_1_subj is not None else ""
        board.bo_2_subj = bo_2_subj if bo_2_subj is not None else ""
        board.bo_3_subj = bo_3_subj if bo_3_subj is not None else ""
        board.bo_4_subj = bo_4_subj if bo_4_subj is not None else ""
        board.bo_5_subj = bo_5_subj if bo_5_subj is not None else ""
        board.bo_6_subj = bo_6_subj if bo_6_subj is not None else ""
        board.bo_7_subj = bo_7_subj if bo_7_subj is not None else ""
        board.bo_8_subj = bo_8_subj if bo_8_subj is not None else ""
        board.bo_9_subj = bo_9_subj if bo_9_subj is not None else ""
        board.bo_10_subj = bo_10_subj if bo_10_subj is not None else ""
        board.bo_1 = bo_1 if bo_1 is not None else ""
        board.bo_2 = bo_2 if bo_2 is not None else ""
        board.bo_3 = bo_3 if bo_3 is not None else ""
        board.bo_4 = bo_4 if bo_4 is not None else ""
        board.bo_5 = bo_5 if bo_5 is not None else ""
        board.bo_6 = bo_6 if bo_6 is not None else ""
        board.bo_7 = bo_7 if bo_7 is not None else ""
        board.bo_8 = bo_8 if bo_8 is not None else ""
        board.bo_9 = bo_9 if bo_9 is not None else ""
        board.bo_10 = bo_10 if bo_10 is not None else ""
        db.commit()
                
    return RedirectResponse(f"/admin/board_form/{bo_table}", status_code=303)

# def test(ttt: Optional[List[str]] = Form(None, alias="ttt[]")):
@router.post("/board_list_update")
def board_list_update(request: Request, db: Session = Depends(get_db),
                      checks: Optional[List[str]] = Form(None, alias="chk[]"),
                      gr_id: Optional[List[str]] = Form(None, alias="gr_id[]"),
                      bo_table: Optional[List[str]] = Form(None, alias="bo_table[]"),
                      bo_skin: Optional[List[str]] = Form(None, alias="bo_skin[]"),
                      bo_mobile_skin: Optional[List[str]] = Form(None, alias="bo_mobile_skin[]"),
                      bo_subject: Optional[List[str]] = Form(None, alias="bo_subject[]"),
                      bo_read_point: Optional[List[int]] = Form(None, alias="bo_read_point[]"),
                      bo_write_point: Optional[List[int]] = Form(None, alias="bo_write_point[]"),
                      bo_comment_point: Optional[List[int]] = Form(None, alias="bo_comment_point[]"),
                      bo_download_point: Optional[List[int]] = Form(None, alias="bo_download_point[]"),
                      bo_use_sns: Optional[List[int]] = Form(None, alias="bo_use_sns[]"),
                      bo_use_search: Optional[List[int]] = Form(None, alias="bo_use_search[]"),
                      bo_device: Optional[List[str]] = Form(None, alias="bo_device[]"),
                      ):
    
    print(checks)
    print(bo_use_sns)
    
    for i in checks:
        i = int(i)
        board = db.query(models.Board).filter(models.Board.bo_table == bo_table[i]).first()
        if board:
    # #         board.gr_id = gr_id[i]
    # #         board.bo_skin = bo_skin[i]
    # #         board.bo_mobile_skin = bo_mobile_skin[i]
    # #         board.bo_subject = bo_subject[i]
    # #         board.bo_read_point = bo_read_point[i]
    # #         board.bo_write_point = bo_write_point[i]
    # #         board.bo_comment_point = bo_comment_point[i]
    # #         board.bo_download_point = bo_download_point[i]
    # #         # board.bo_use_sns = get_from_list(bo_use_sns, i, 0)
            # board.bo_use_sns = 1 if i in bo_use_sns is not None else 0
            
            try:
                board.bo_use_sns = 1 if i in bo_use_sns is not None else 0
            except (TypeError, IndexError):
                board.bo_use_sns = 0
            board.bo_use_search = get_from_list(bo_use_search, i, 0)
            
            # checkbox 에 값을 집어 넣는것 까지 하다가 어느 정도 결과가 나와서 퇴근함 kagla 230922 17:50
            # checkbox 에 value = 0, 1, 2, 3... n 으로 증가시켜야 함 (주의)
            
    #         board.bo_device = bo_device[i]
            db.commit()
    
    return RedirectResponse("/admin/board_list", status_code=303)

# 논리적인 오류가 있음
def get_from_list(lst, index, default=0):
    try:
        return 1 if index in lst is not None else default
    except (TypeError, IndexError):
        return default
    
# def get_from_list(lst, index, default=None):
#     if lst is None:
#         return default
#     try:
#         return lst[index]
#     except IndexError:
#         return default    