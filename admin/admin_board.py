import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from database import get_db, engine
import models 
from common import *
from typing import List, Optional
from dataclassform import BoardForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = Jinja2Templates(directory=[ADMIN_TEMPLATES_DIR, EDITOR_PATH])
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_token"] = generate_token
templates.env.globals["editor_path"] = editor_path
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

@router.get("/board_list")
def board_list(request: Request, db: Session = Depends(get_db), search_params: dict = Depends(common_search_query_params)):
        # sst: str = Query(default=""), # sort field (정렬 필드)
        # sod: str = Query(default=""), # search order (검색 오름, 내림차순)
        # sfl: str = Query(default=""), # search field (검색 필드)
        # stx: str = Query(default=""), # search text (검색어)
        # current_page: int = Query(default=1, alias="page"), # 페이지
        # ):
    '''
    게시판관리 목록
    '''
    request.session["menu_key"] = "300100"
    
    # # 초기 쿼리 설정
    # query = db.query(models.Board)
    # records_per_page = request.state.config.cf_page_rows

    # # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    # if sst is not None and sst != "":
    #     if sod == "desc":
    #         query = query.order_by(desc(getattr(models.Board, sst)))
    #     else:
    #         query = query.order_by(asc(getattr(models.Board, sst)))

    # # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    # if sfl is not None and stx is not None:
    #     if hasattr(models.Board, sfl):  # sfl이 models.Board에 존재하는지 확인
    #         if sfl in ["gr_id", "bo_table"]:
    #             query = query.filter(getattr(models.Board, sfl) == stx)
    #         else:
    #             query = query.filter(getattr(models.Board, sfl).like(f"%{stx}%"))
            
    # # 페이지 번호에 따른 offset 계산
    # offset = (current_page - 1) * records_per_page

    # # 최종 쿼리 결과를 가져옵니다.
    # boards = query.offset(offset).limit(records_per_page).all()
    # # 전체 레코드 개수 계산
    # total_records = query.count()
    
    result = select_query(
                request, 
                models.Board, 
                search_params, 
                same_search_fields = ["gr_id", "bo_table"], 
            )
    
    context = {
        "request": request,
        "boards": result['rows'],
        "total_count": result['total_count'],
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("board_list.html", context)


@router.post("/board_list_update")
async def board_list_update(request: Request, db: Session = Depends(get_db),
        token: Optional[str] = Form(...),
        checks: Optional[List[int]] = Form(None, alias="chk[]"),
        gr_id: Optional[List[str]] = Form(None, alias="gr_id[]"),
        bo_table: Optional[List[str]] = Form(None, alias="bo_table[]"),
        bo_skin: Optional[List[str]] = Form(None, alias="bo_skin[]"),
        bo_mobile_skin: Optional[List[str]] = Form(None, alias="bo_mobile_skin[]"),
        bo_subject: Optional[List[str]] = Form(None, alias="bo_subject[]"),
        bo_read_point: Optional[List[str]] = Form(None, alias="bo_read_point[]"),
        bo_write_point: Optional[List[str]] = Form(None, alias="bo_write_point[]"),
        bo_comment_point: Optional[List[str]] = Form(None, alias="bo_comment_point[]"),
        bo_download_point: Optional[List[str]] = Form(None, alias="bo_download_point[]"),
        bo_use_sns: Optional[List[int]] = Form(None, alias="bo_use_sns[]"),
        bo_use_search: Optional[List[int]] = Form(None, alias="bo_use_search[]"),
        bo_order: Optional[List[str]] = Form(None, alias="bo_order[]"),
        bo_device: Optional[List[str]] = Form(None, alias="bo_device[]"),
        act_button: Optional[str] = Form(...),
        ):
    
    if not compare_token(request, token, 'board_list'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰값이 일치하지 않습니다."]})

    query_string = generate_query_string(request)
    
    if act_button == "선택삭제":
        for i in checks:
            board = db.query(models.Board).filter(models.Board.bo_table == bo_table[i]).first()
            if board:
                # 게시판 관리 레코드 삭제
                db.delete(board)
                db.commit()
                # 게시판 테이블 삭제
                models.Write = dynamic_create_write_table(table_name=board.bo_table, create_table=False)
                models.Write.__table__.drop(engine)
                # 최신글 캐시 삭제
                G6FileCache().delete_prefix(f'latest-{board.bo_table}')
        return RedirectResponse(f"/admin/board_list?{query_string}", status_code=303)
        
    # 선택수정
    for i in checks:
        board = db.query(models.Board).filter(models.Board.bo_table == bo_table[i]).first()
        if board:
            board.gr_id = gr_id[i]
            board.bo_skin = bo_skin[i]
            board.bo_mobile_skin = bo_mobile_skin[i]
            board.bo_subject = bo_subject[i]
            board.bo_read_point = int(bo_read_point[i]) if bo_read_point[i] is not None and bo_read_point[i].isdigit() else 0
            board.bo_write_point = int(bo_write_point[i]) if bo_write_point[i] is not None and bo_write_point[i].isdigit() else 0
            board.bo_comment_point = int(bo_comment_point[i]) if bo_comment_point[i] is not None and bo_comment_point[i].isdigit() else 0
            board.bo_download_point = int(bo_download_point[i]) if bo_download_point[i] is not None and bo_download_point[i].isdigit() else 0
            
            # try:
            #     board.bo_use_sns = 1 if i in bo_use_sns is not None else 0
            # except (TypeError, IndexError):
            #     board.bo_use_sns = 0
            board.bo_use_sns = get_from_list(bo_use_sns, i, 0)
            board.bo_use_search = get_from_list(bo_use_search, i, 0)
            
            # checkbox 에 값을 집어 넣는것 까지 하다가 어느 정도 결과가 나와서 퇴근함 kagla 230922 17:50
            # checkbox 에 value = 0, 1, 2, 3... n 으로 증가시켜야 함 (주의)
    
            board.bo_order = int(bo_order[i]) if bo_order[i] is not None and bo_order[i].isdigit() else 0
            board.bo_device = bo_device[i] if bo_device[i] is not None else ""
            db.commit()

            # 최신글 캐시 삭제
            G6FileCache().delete_prefix(f'latest-{board.bo_table}')
            
    return RedirectResponse(f"/admin/board_list?{query_string}", status_code=303)


# 등록 폼
@router.get("/board_form")
def board_form(request: Request, db: Session = Depends(get_db)):
    # token = hash_password(hash_password("")) # 토큰값을 아무도 알수 없게 만듬
    # request.session["token"] = token   
    
    config = request.state.config
    
    board = {
        "bo_table": "",
        "bo_count_delete" : 1,
        "bo_count_modify" : 1,
        "bo_read_point" : config.cf_read_point,
        "bo_write_point" : config.cf_write_point,
        "bo_comment_point" : config.cf_comment_point,
        "bo_download_point" : config.cf_download_point,
        "bo_gallery_cols" : 4,
        "bo_gallery_width" : 200,
        "bo_gallery_height" : 150,
        "bo_mobile_gallery_width" : 125,
        "bo_mobile_gallery_height" : 100,
        "bo_table_width" : 100,
        "bo_page_rows" : config.cf_page_rows,
        "bo_mobile_page_rows" : config.cf_mobile_page_rows,
        "bo_subject_len" : 60,
        "bo_mobile_subject_len" : 30,
        "bo_new" : 24,
        "bo_hot" : 100,
        "bo_image_width" : 600,
        "bo_upload_count" : 2,
        "bo_upload_size" : 1048576,
        "bo_reply_order" : 1,
        "bo_use_search" : 1,
        "bo_skin" : "basic",
        "bo_mobile_skin" : "basic",
        "bo_use_secret" : 0,
    }
    
    context = {
        "request": request,
        # "board": None,
        "board": board,
        "config": config,
    }
    return templates.TemplateResponse("board_form.html", context)


# 수정 폼
@router.get("/board_form/{bo_table}")
async def board_form(bo_table: str, request: Request, db: Session = Depends(get_db),
               sfl: Optional[str] = None, 
               stx: Optional[str] = None, ):
    
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        # raise HTTPException(status_code=404, detail=f"{bo_table} Board is not found.")
        errors = [f"{bo_table} 게시판이 존재하지 않습니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})

    # 토큰값을 게시판아이디로 만들어 세션에 저장하고 수정시 넘어오는 토큰값을 비교하여 수정 상태임을 확인
    token = hash_password(bo_table)
    request.session["token"] = token
    
    context = {
        "request": request,
        "board": board,
        "token": token,
        "config": request.state.config,
    }
    return templates.TemplateResponse("board_form.html", context)


# 등록, 수정 처리
@router.post("/board_form_update")  
def board_form_update(request: Request, 
                        db: Session = Depends(get_db),
                        sfl: str = Form(None),
                        stx: str = Form(None),
                        token: str = Form(None),
                        bo_table: str = Form(...),
                        form_data: BoardForm = Depends(), 
                        
                        chk_grp_device: str = Form(None),
                        chk_grp_category_list: str = Form(None),
                        chk_grp_admin: str = Form(None),
                        chk_grp_list_level: str = Form(None),
                        chk_grp_read_level: str = Form(None),
                        chk_grp_write_level: str = Form(None),
                        chk_grp_reply_level: str = Form(None),
                        chk_grp_comment_level: str = Form(None),
                        chk_grp_link_level: str = Form(None),
                        chk_grp_upload_level: str = Form(None),
                        chk_grp_download_level: str = Form(None),
                        chk_grp_html_level: str = Form(None),
                        chk_grp_count_modify: str = Form(None),
                        chk_grp_count_delete: str = Form(None),
                        chk_grp_use_sideview: str = Form(None),
                        chk_grp_use_secret: str = Form(None),
                        chk_grp_use_dhtml_editor: str = Form(None),
                        chk_grp_select_editor: str = Form(None),
                        chk_grp_use_rss_view: str = Form(None),
                        chk_grp_use_good: str = Form(None),
                        chk_grp_use_nogood: str = Form(None),
                        chk_grp_use_name: str = Form(None),
                        chk_grp_use_signature: str = Form(None),
                        chk_grp_use_ip_view: str = Form(None),
                        chk_grp_use_list_content: str = Form(None),
                        chk_grp_use_list_file: str = Form(None),
                        chk_grp_use_list_view: str = Form(None),
                        chk_grp_use_email: str = Form(None),
                        chk_grp_use_cert: str = Form(None),
                        chk_grp_upload_count: str = Form(None),
                        chk_grp_upload_size: str = Form(None),
                        chk_grp_use_file_content: str = Form(None),
                        chk_grp_write_min: str = Form(None),
                        chk_grp_write_max: str = Form(None),
                        chk_grp_comment_min: str = Form(None),
                        chk_grp_comment_max: str = Form(None),
                        chk_grp_use_sns: str = Form(None),
                        chk_grp_use_search: str = Form(None),
                        chk_grp_order: str = Form(None),
                        chk_grp_use_captcha: str = Form(None),
                        chk_grp_skin: str = Form(None),
                        chk_grp_mobile_skin: str = Form(None),
                        chk_grp_include_head: str = Form(None),
                        chk_grp_include_tail: str = Form(None),
                        chk_grp_content_head: str = Form(None),
                        chk_grp_content_tail: str = Form(None),
                        chk_grp_mobile_content_head: str = Form(None),
                        chk_grp_mobile_content_tail: str = Form(None),
                        chk_grp_insert_content: str = Form(None),
                        chk_grp_subject_len: str = Form(None),
                        chk_grp_mobile_subject_len: str = Form(None),
                        chk_grp_page_rows: str = Form(None),
                        chk_grp_mobile_page_rows: str = Form(None),
                        chk_grp_gallery_cols: str = Form(None),
                        chk_grp_gallery_width: str = Form(None),
                        chk_grp_gallery_height: str = Form(None),
                        chk_grp_mobile_gallery_width: str = Form(None),
                        chk_grp_mobile_gallery_height: str = Form(None),
                        chk_grp_table_width: str = Form(None),
                        chk_grp_image_width: str = Form(None),
                        chk_grp_new: str = Form(None),
                        chk_grp_hot: str = Form(None),
                        chk_grp_reply_order: str = Form(None),
                        chk_grp_sort_field: str = Form(None),
                        chk_grp_read_point: str = Form(None),
                        chk_grp_write_point: str = Form(None),
                        chk_grp_comment_point: str = Form(None),
                        chk_grp_download_point: str = Form(None),
                        chk_grp_1: str = Form(None),
                        chk_grp_2: str = Form(None),
                        chk_grp_3: str = Form(None),
                        chk_grp_4: str = Form(None),
                        chk_grp_5: str = Form(None),
                        chk_grp_6: str = Form(None),
                        chk_grp_7: str = Form(None),
                        chk_grp_8: str = Form(None),
                        chk_grp_9: str = Form(None),
                        chk_grp_10: str = Form(None),
                        
                        chk_all_device: str = Form(None),
                        chk_all_category_list: str = Form(None),
                        chk_all_admin: str = Form(None),
                        chk_all_list_level: str = Form(None),
                        chk_all_read_level: str = Form(None),
                        chk_all_write_level: str = Form(None),
                        chk_all_reply_level: str = Form(None),
                        chk_all_comment_level: str = Form(None),
                        chk_all_link_level: str = Form(None),
                        chk_all_upload_level: str = Form(None),
                        chk_all_download_level: str = Form(None),
                        chk_all_html_level: str = Form(None),
                        chk_all_count_modify: str = Form(None),
                        chk_all_count_delete: str = Form(None),
                        chk_all_use_sideview: str = Form(None),
                        chk_all_use_secret: str = Form(None),
                        chk_all_use_dhtml_editor: str = Form(None),
                        chk_all_select_editor: str = Form(None),
                        chk_all_use_rss_view: str = Form(None),
                        chk_all_use_good: str = Form(None),
                        chk_all_use_nogood: str = Form(None),
                        chk_all_use_name: str = Form(None),
                        chk_all_use_signature: str = Form(None),
                        chk_all_use_ip_view: str = Form(None),
                        chk_all_use_list_content: str = Form(None),
                        chk_all_use_list_file: str = Form(None),
                        chk_all_use_list_view: str = Form(None),
                        chk_all_use_email: str = Form(None),
                        chk_all_use_cert: str = Form(None),
                        chk_all_upload_count: str = Form(None),
                        chk_all_upload_size: str = Form(None),
                        chk_all_use_file_content: str = Form(None),
                        chk_all_write_min: str = Form(None),
                        chk_all_write_max: str = Form(None),
                        chk_all_comment_min: str = Form(None),
                        chk_all_comment_max: str = Form(None),
                        chk_all_use_sns: str = Form(None),
                        chk_all_use_search: str = Form(None),
                        chk_all_order: str = Form(None),
                        chk_all_use_captcha: str = Form(None),
                        chk_all_skin: str = Form(None),
                        chk_all_mobile_skin: str = Form(None),
                        chk_all_include_head: str = Form(None),
                        chk_all_include_tail: str = Form(None),
                        chk_all_content_head: str = Form(None),
                        chk_all_content_tail: str = Form(None),
                        chk_all_mobile_content_head: str = Form(None),
                        chk_all_mobile_content_tail: str = Form(None),
                        chk_all_insert_content: str = Form(None),
                        chk_all_subject_len: str = Form(None),
                        chk_all_mobile_subject_len: str = Form(None),
                        chk_all_page_rows: str = Form(None),
                        chk_all_mobile_page_rows: str = Form(None),
                        chk_all_gallery_cols: str = Form(None),
                        chk_all_gallery_width: str = Form(None),
                        chk_all_gallery_height: str = Form(None),
                        chk_all_mobile_gallery_width: str = Form(None),
                        chk_all_mobile_gallery_height: str = Form(None),
                        chk_all_table_width: str = Form(None),
                        chk_all_image_width: str = Form(None),
                        chk_all_new: str = Form(None),
                        chk_all_hot: str = Form(None),
                        chk_all_reply_order: str = Form(None),
                        chk_all_sort_field: str = Form(None),
                        chk_all_read_point: str = Form(None),
                        chk_all_write_point: str = Form(None),
                        chk_all_comment_point: str = Form(None),
                        chk_all_download_point: str = Form(None),
                        chk_all_1: str = Form(None),
                        chk_all_2: str = Form(None),
                        chk_all_3: str = Form(None),
                        chk_all_4: str = Form(None),
                        chk_all_5: str = Form(None),
                        chk_all_6: str = Form(None),
                        chk_all_7: str = Form(None),
                        chk_all_8: str = Form(None),
                        chk_all_9: str = Form(None),
                        chk_all_10: str = Form(None),
                        ):

    if compare_token(request, token, 'insert'):
        existing_board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
        if existing_board:
            errors = [f"{bo_table} 게시판아이디가 이미 존재합니다. (등록불가)"]
            return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
        
        new_board = models.Board(bo_table=bo_table, **form_data.__dict__)
        db.add(new_board)
        db.commit()
        
        # 게시판 테이블 생성
        models.Write = dynamic_create_write_table(table_name=bo_table, create_table=True)        
        
    # else: # 수정
    elif compare_token(request, token, 'update'):
        existing_board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
        if not existing_board:
            return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{bo_table} 게시판아이디가 존재하지 않습니다. (수정불가)"]})
        
        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_board, field, value)
        db.commit()
        
    else:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["잘못된 접근입니다."]})

    # 그룹적용
    chk_grp = {}
    if chk_grp_device: chk_grp['bo_device'] = form_data.bo_device
    if chk_grp_category_list: 
        chk_grp['bo_category_list'] = form_data.bo_category_list
        chk_grp['bo_use_category'] = form_data.bo_use_category
    if chk_grp_admin: chk_grp['bo_admin'] = form_data.bo_admin
    if chk_grp_list_level: chk_grp['bo_list_level'] = form_data.bo_list_level
    if chk_grp_read_level: chk_grp['bo_read_level'] = form_data.bo_read_level
    if chk_grp_write_level: chk_grp['bo_write_level'] = form_data.bo_write_level
    if chk_grp_reply_level: chk_grp['bo_reply_level'] = form_data.bo_reply_level
    if chk_grp_comment_level: chk_grp['bo_comment_level'] = form_data.bo_comment_level
    if chk_grp_link_level: chk_grp['bo_link_level'] = form_data.bo_link_level
    if chk_grp_upload_level: chk_grp['bo_upload_level'] = form_data.bo_upload_level
    if chk_grp_download_level: chk_grp['bo_download_level'] = form_data.bo_download_level
    if chk_grp_html_level: chk_grp['bo_html_level'] = form_data.bo_html_level
    if chk_grp_count_modify: chk_grp['bo_count_modify'] = form_data.bo_count_modify
    if chk_grp_count_delete: chk_grp['bo_count_delete'] = form_data.bo_count_delete
    if chk_grp_use_sideview: chk_grp['bo_use_sideview'] = form_data.bo_use_sideview
    if chk_grp_use_secret: chk_grp['bo_use_secret'] = form_data.bo_use_secret
    if chk_grp_use_dhtml_editor: chk_grp['bo_use_dhtml_editor'] = form_data.bo_use_dhtml_editor
    if chk_grp_select_editor: chk_grp['bo_select_editor'] = form_data.bo_select_editor
    if chk_grp_use_rss_view: chk_grp['bo_use_rss_view'] = form_data.bo_use_rss_view
    if chk_grp_use_good: chk_grp['bo_use_good'] = form_data.bo_use_good
    if chk_grp_use_nogood: chk_grp['bo_use_nogood'] = form_data.bo_use_nogood
    if chk_grp_use_name: chk_grp['bo_use_name'] = form_data.bo_use_name
    if chk_grp_use_signature: chk_grp['bo_use_signature'] = form_data.bo_use_signature
    if chk_grp_use_ip_view: chk_grp['bo_use_ip_view'] = form_data.bo_use_ip_view
    if chk_grp_use_list_content: chk_grp['bo_use_list_content'] = form_data.bo_use_list_content
    if chk_grp_use_list_file: chk_grp['bo_use_list_file'] = form_data.bo_use_list_file
    if chk_grp_use_list_view: chk_grp['bo_use_list_view'] = form_data.bo_use_list_view
    if chk_grp_use_email: chk_grp['bo_use_email'] = form_data.bo_use_email
    if chk_grp_use_cert: chk_grp['bo_use_cert'] = form_data.bo_use_cert
    if chk_grp_upload_count: chk_grp['bo_upload_count'] = form_data.bo_upload_count
    if chk_grp_upload_size: chk_grp['bo_upload_size'] = form_data.bo_upload_size
    if chk_grp_use_file_content: chk_grp['bo_use_file_content'] = form_data.bo_use_file_content
    if chk_grp_write_min: chk_grp['bo_write_min'] = form_data.bo_write_min
    if chk_grp_write_max: chk_grp['bo_write_max'] = form_data.bo_write_max
    if chk_grp_comment_min: chk_grp['bo_comment_min'] = form_data.bo_comment_min
    if chk_grp_comment_max: chk_grp['bo_comment_max'] = form_data.bo_comment_max
    if chk_grp_use_sns: chk_grp['bo_use_sns'] = form_data.bo_use_sns
    if chk_grp_use_search: chk_grp['bo_use_search'] = form_data.bo_use_search
    if chk_grp_order: chk_grp['bo_order'] = form_data.bo_order
    if chk_grp_use_captcha: chk_grp['bo_use_captcha'] = form_data.bo_use_captcha
    if chk_grp_skin: chk_grp['bo_skin'] = form_data.bo_skin
    if chk_grp_mobile_skin: chk_grp['bo_mobile_skin'] = form_data.bo_mobile_skin
    if chk_grp_include_head: chk_grp['bo_include_head'] = form_data.bo_include_head
    if chk_grp_include_tail: chk_grp['bo_include_tail'] = form_data.bo_include_tail
    if chk_grp_content_head: chk_grp['bo_content_head'] = form_data.bo_content_head
    if chk_grp_content_tail: chk_grp['bo_content_tail'] = form_data.bo_content_tail
    if chk_grp_mobile_content_head: chk_grp['bo_mobile_content_head'] = form_data.bo_mobile_content_head
    if chk_grp_mobile_content_tail: chk_grp['bo_mobile_content_tail'] = form_data.bo_mobile_content_tail
    if chk_grp_insert_content: chk_grp['bo_insert_content'] = form_data.bo_insert_content
    if chk_grp_subject_len: chk_grp['bo_subject_len'] = form_data.bo_subject_len
    if chk_grp_mobile_subject_len: chk_grp['bo_mobile_subject_len'] = form_data.bo_mobile_subject_len
    if chk_grp_page_rows: chk_grp['bo_page_rows'] = form_data.bo_page_rows
    if chk_grp_mobile_page_rows: chk_grp['bo_mobile_page_rows'] = form_data.bo_mobile_page_rows
    if chk_grp_gallery_cols: chk_grp['bo_gallery_cols'] = form_data.bo_gallery_cols
    if chk_grp_gallery_width: chk_grp['bo_gallery_width'] = form_data.bo_gallery_width
    if chk_grp_gallery_height: chk_grp['bo_gallery_height'] = form_data.bo_gallery_height
    if chk_grp_mobile_gallery_width: chk_grp['bo_mobile_gallery_width'] = form_data.bo_mobile_gallery_width
    if chk_grp_mobile_gallery_height: chk_grp['bo_mobile_gallery_height'] = form_data.bo_mobile_gallery_height
    if chk_grp_table_width: chk_grp['bo_table_width'] = form_data.bo_table_width
    if chk_grp_image_width: chk_grp['bo_image_width'] = form_data.bo_image_width
    if chk_grp_new: chk_grp['bo_new'] = form_data.bo_new
    if chk_grp_hot: chk_grp['bo_hot'] = form_data.bo_hot
    if chk_grp_reply_order: chk_grp['bo_reply_order'] = form_data.bo_reply_order
    if chk_grp_sort_field: chk_grp['bo_sort_field'] = form_data.bo_sort_field
    if chk_grp_read_point: chk_grp['bo_read_point'] = form_data.bo_read_point
    if chk_grp_write_point: chk_grp['bo_write_point'] = form_data.bo_write_point
    if chk_grp_comment_point: chk_grp['bo_comment_point'] = form_data.bo_comment_point
    if chk_grp_download_point: chk_grp['bo_download_point'] = form_data.bo_download_point
    if chk_grp_1: 
        chk_grp['bo_1_subj'] = form_data.bo_1_subj
        chk_grp['bo_1'] = form_data.bo_1
    if chk_grp_2: 
        chk_grp['bo_2_subj'] = form_data.bo_2_subj
        chk_grp['bo_2'] = form_data.bo_2
    if chk_grp_3: 
        chk_grp['bo_3_subj'] = form_data.bo_3_subj
        chk_grp['bo_3'] = form_data.bo_3
    if chk_grp_4: 
        chk_grp['bo_4_subj'] = form_data.bo_4_subj
        chk_grp['bo_4'] = form_data.bo_4
    if chk_grp_5: 
        chk_grp['bo_5_subj'] = form_data.bo_5_subj
        chk_grp['bo_5'] = form_data.bo_5
    if chk_grp_6: 
        chk_grp['bo_6_subj'] = form_data.bo_6_subj
        chk_grp['bo_6'] = form_data.bo_6
    if chk_grp_7: 
        chk_grp['bo_7_subj'] = form_data.bo_7_subj
        chk_grp['bo_7'] = form_data.bo_7
    if chk_grp_8: 
        chk_grp['bo_8_subj'] = form_data.bo_8_subj
        chk_grp['bo_8'] = form_data.bo_8
    if chk_grp_9: 
        chk_grp['bo_9_subj'] = form_data.bo_9_subj
        chk_grp['bo_9'] = form_data.bo_9
    if chk_grp_10: 
        chk_grp['bo_10_subj'] = form_data.bo_10_subj
        chk_grp['bo_10'] = form_data.bo_10    
            
    # 전체적용
    chk_all = {}
    if chk_all_device: chk_all['bo_device'] = form_data.bo_device
    if chk_all_category_list: 
        chk_all['bo_category_list'] = form_data.bo_category_list
        chk_all['bo_use_category'] = form_data.bo_use_category
    if chk_all_admin: chk_all['bo_admin'] = form_data.bo_admin
    if chk_all_list_level: chk_all['bo_list_level'] = form_data.bo_list_level
    if chk_all_read_level: chk_all['bo_read_level'] = form_data.bo_read_level
    if chk_all_write_level: chk_all['bo_write_level'] = form_data.bo_write_level
    if chk_all_reply_level: chk_all['bo_reply_level'] = form_data.bo_reply_level
    if chk_all_comment_level: chk_all['bo_comment_level'] = form_data.bo_comment_level
    if chk_all_link_level: chk_all['bo_link_level'] = form_data.bo_link_level
    if chk_all_upload_level: chk_all['bo_upload_level'] = form_data.bo_upload_level
    if chk_all_download_level: chk_all['bo_download_level'] = form_data.bo_download_level
    if chk_all_html_level: chk_all['bo_html_level'] = form_data.bo_html_level
    if chk_all_count_modify: chk_all['bo_count_modify'] = form_data.bo_count_modify
    if chk_all_count_delete: chk_all['bo_count_delete'] = form_data.bo_count_delete
    if chk_all_use_sideview: chk_all['bo_use_sideview'] = form_data.bo_use_sideview
    if chk_all_use_secret: chk_all['bo_use_secret'] = form_data.bo_use_secret
    if chk_all_use_dhtml_editor: chk_all['bo_use_dhtml_editor'] = form_data.bo_use_dhtml_editor
    if chk_all_select_editor: chk_all['bo_select_editor'] = form_data.bo_select_editor
    if chk_all_use_rss_view: chk_all['bo_use_rss_view'] = form_data.bo_use_rss_view
    if chk_all_use_good: chk_all['bo_use_good'] = form_data.bo_use_good
    if chk_all_use_nogood: chk_all['bo_use_nogood'] = form_data.bo_use_nogood
    if chk_all_use_name: chk_all['bo_use_name'] = form_data.bo_use_name
    if chk_all_use_signature: chk_all['bo_use_signature'] = form_data.bo_use_signature
    if chk_all_use_ip_view: chk_all['bo_use_ip_view'] = form_data.bo_use_ip_view
    if chk_all_use_list_content: chk_all['bo_use_list_content'] = form_data.bo_use_list_content
    if chk_all_use_list_file: chk_all['bo_use_list_file'] = form_data.bo_use_list_file
    if chk_all_use_list_view: chk_all['bo_use_list_view'] = form_data.bo_use_list_view
    if chk_all_use_email: chk_all['bo_use_email'] = form_data.bo_use_email
    if chk_all_use_cert: chk_all['bo_use_cert'] = form_data.bo_use_cert
    if chk_all_upload_count: chk_all['bo_upload_count'] = form_data.bo_upload_count
    if chk_all_upload_size: chk_all['bo_upload_size'] = form_data.bo_upload_size
    if chk_all_use_file_content: chk_all['bo_use_file_content'] = form_data.bo_use_file_content
    if chk_all_write_min: chk_all['bo_write_min'] = form_data.bo_write_min
    if chk_all_write_max: chk_all['bo_write_max'] = form_data.bo_write_max
    if chk_all_comment_min: chk_all['bo_comment_min'] = form_data.bo_comment_min
    if chk_all_comment_max: chk_all['bo_comment_max'] = form_data.bo_comment_max
    if chk_all_use_sns: chk_all['bo_use_sns'] = form_data.bo_use_sns
    if chk_all_use_search: chk_all['bo_use_search'] = form_data.bo_use_search
    if chk_all_order: chk_all['bo_order'] = form_data.bo_order
    if chk_all_use_captcha: chk_all['bo_use_captcha'] = form_data.bo_use_captcha
    if chk_all_skin: chk_all['bo_skin'] = form_data.bo_skin
    if chk_all_mobile_skin: chk_all['bo_mobile_skin'] = form_data.bo_mobile_skin
    if chk_all_include_head: chk_all['bo_include_head'] = form_data.bo_include_head
    if chk_all_include_tail: chk_all['bo_include_tail'] = form_data.bo_include_tail
    if chk_all_content_head: chk_all['bo_content_head'] = form_data.bo_content_head
    if chk_all_content_tail: chk_all['bo_content_tail'] = form_data.bo_content_tail
    if chk_all_mobile_content_head: chk_all['bo_mobile_content_head'] = form_data.bo_mobile_content_head
    if chk_all_mobile_content_tail: chk_all['bo_mobile_content_tail'] = form_data.bo_mobile_content_tail
    if chk_all_insert_content: chk_all['bo_insert_content'] = form_data.bo_insert_content
    if chk_all_subject_len: chk_all['bo_subject_len'] = form_data.bo_subject_len
    if chk_all_mobile_subject_len: chk_all['bo_mobile_subject_len'] = form_data.bo_mobile_subject_len
    if chk_all_page_rows: chk_all['bo_page_rows'] = form_data.bo_page_rows
    if chk_all_mobile_page_rows: chk_all['bo_mobile_page_rows'] = form_data.bo_mobile_page_rows
    if chk_all_gallery_cols: chk_all['bo_gallery_cols'] = form_data.bo_gallery_cols
    if chk_all_gallery_width: chk_all['bo_gallery_width'] = form_data.bo_gallery_width
    if chk_all_gallery_height: chk_all['bo_gallery_height'] = form_data.bo_gallery_height
    if chk_all_mobile_gallery_width: chk_all['bo_mobile_gallery_width'] = form_data.bo_mobile_gallery_width
    if chk_all_mobile_gallery_height: chk_all['bo_mobile_gallery_height'] = form_data.bo_mobile_gallery_height
    if chk_all_table_width: chk_all['bo_table_width'] = form_data.bo_table_width
    if chk_all_image_width: chk_all['bo_image_width'] = form_data.bo_image_width
    if chk_all_new: chk_all['bo_new'] = form_data.bo_new
    if chk_all_hot: chk_all['bo_hot'] = form_data.bo_hot
    if chk_all_reply_order: chk_all['bo_reply_order'] = form_data.bo_reply_order
    if chk_all_sort_field: chk_all['bo_sort_field'] = form_data.bo_sort_field
    if chk_all_read_point: chk_all['bo_read_point'] = form_data.bo_read_point
    if chk_all_write_point: chk_all['bo_write_point'] = form_data.bo_write_point
    if chk_all_comment_point: chk_all['bo_comment_point'] = form_data.bo_comment_point
    if chk_all_download_point: chk_all['bo_download_point'] = form_data.bo_download_point
    if chk_all_1: 
        chk_all['bo_1_subj'] = form_data.bo_1_subj
        chk_all['bo_1'] = form_data.bo_1
    if chk_all_2: 
        chk_all['bo_2_subj'] = form_data.bo_2_subj        
        chk_all['bo_2'] = form_data.bo_2
    if chk_all_3: 
        chk_all['bo_3_subj'] = form_data.bo_3_subj        
        chk_all['bo_3'] = form_data.bo_3
    if chk_all_4: 
        chk_all['bo_4_subj'] = form_data.bo_4_subj        
        chk_all['bo_4'] = form_data.bo_4
    if chk_all_5: 
        chk_all['bo_5_subj'] = form_data.bo_5_subj        
        chk_all['bo_5'] = form_data.bo_5
    if chk_all_6: 
        chk_all['bo_6_subj'] = form_data.bo_6_subj        
        chk_all['bo_6'] = form_data.bo_6
    if chk_all_7: 
        chk_all['bo_7_subj'] = form_data.bo_7_subj     
        chk_all['bo_7'] = form_data.bo_7
    if chk_all_8: 
        chk_all['bo_8_subj'] = form_data.bo_8_subj        
        chk_all['bo_8'] = form_data.bo_8
    if chk_all_9: 
        chk_all['bo_9_subj'] = form_data.bo_9_subj        
        chk_all['bo_9'] = form_data.bo_9
    if chk_all_10: 
        chk_all['bo_10_subj'] = form_data.bo_10_subj        
        chk_all['bo_10'] = form_data.bo_10
     
    # 그룹적용 체크한 항목이 있다면    
    if (chk_grp):
        boards = db.query(models.Board).filter(models.Board.gr_id == form_data.gr_id).all()
        for board in boards:
            for key, value in chk_grp.items():
                setattr(board, key, value) 
            db.commit()

    # 전체적용 체크한 항목이 있다면    
    if (chk_all):
        boards = db.query(models.Board).all()
        for board in boards:
            for key, value in chk_all.items():
                setattr(board, key, value) 
            db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')
            
    query_string = generate_query_string(request)
            
    return RedirectResponse(f"/admin/board_form/{bo_table}?{query_string}", status_code=303)


@router.get("/board_copy/{bo_table}")
async def board_copy(request: Request, bo_table: str, db: Session = Depends(get_db)):
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    return templates.TemplateResponse("board_copy.html", {"request": request, "board": board})


@router.post("/board_copy_update")
def board_copy_update(request: Request, db: Session = Depends(get_db),
                      bo_table: Optional[str] = Form(...),
                      target_table: Optional[str] = Form(...),
                      target_subject: Optional[str] = Form(...),
                      copy_case: Optional[str] = Form(...),
                      ):
    
    source_row = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not source_row:
        raise HTTPException(status_code=404, detail=f"{bo_table} is not exists")
    
    target_row = db.query(models.Board).filter(models.Board.bo_table == target_table).first()
    if target_row:
        raise HTTPException(status_code=404, detail=f"{target_table} is already exists")
    
    # 복사될 레코드의 모든 필드를 딕셔너리로 변환
    target_dict = {key: value for key, value in source_row.__dict__.items() if not key.startswith('_')}
    
    target_dict['bo_table'] = target_table
    target_dict['bo_subject'] = target_subject
    
    target_row = models.Board(**target_dict)
    db.add(target_row)
    db.commit()
    
    # 새로운 게시판 테이블 생성
    # source_table 에서 target_table 로 스키마 또는 데이터를 복사하는 코드를 작성해야 함
    models.Write = dynamic_create_write_table(table_name=target_table, create_table=True)
    # 복사 유형을 '구조와 데이터' 선택시 테이블의 레코드 모두 복사
    if copy_case == 'schema_data_both':
        writes = db.query(models.Write).all()
        if writes:
            for write in writes:
                write.bo_table = target_table
                db.add(write)
                db.commit()
                
    content = """
    <script>
        window.opener.location.href = "/admin/board_list";
        window.close();
    </script>
    """
    
    # return RedirectResponse("/admin/board_list", status_code=303)
    return HTMLResponse(content=content)