from fastapi import APIRouter, Depends, Request, Form, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

from common.database import db_session, engine
from common.models import Board, BoardNew, Scrap, BoardFile, BoardGood
from common.formclass import BoardForm
from lib.common import *

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link

BOARD_MENU_KEY = "300100"


@router.get("/board_list")
async def board_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    게시판관리 목록
    """
    request.session["menu_key"] = BOARD_MENU_KEY

    result = select_query(
        request,
        Board,
        search_params,
        same_search_fields=["gr_id", "bo_table"],
    )

    context = {
        "request": request,
        "boards": result['rows'],
        "total_count": result['total_count'],
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("board_list.html", context)


@router.post("/board_list_update", dependencies=[Depends(validate_token)])
async def board_list_update(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
    bo_table: List[str] = Form(None, alias="bo_table[]"),
    bo_skin: List[str] = Form(None, alias="bo_skin[]"),
    bo_mobile_skin: List[str] = Form(None, alias="bo_mobile_skin[]"),
    bo_subject: List[str] = Form(None, alias="bo_subject[]"),
    bo_read_point: List[str] = Form(None, alias="bo_read_point[]"),
    bo_write_point: List[str] = Form(None, alias="bo_write_point[]"),
    bo_comment_point: List[str] = Form(None, alias="bo_comment_point[]"),
    bo_download_point: List[str] = Form(None, alias="bo_download_point[]"),
    bo_use_sns: List[int] = Form(None, alias="bo_use_sns[]"),
    bo_use_search: List[int] = Form(None, alias="bo_use_search[]"),
    bo_order: List[str] = Form(None, alias="bo_order[]"),
    bo_device: List[str] = Form(None, alias="bo_device[]"),
):
    """
    게시판관리 목록 일괄수정
    """
    for i in checks:
        board = db.get(Board, bo_table[i])
        if board:
            board.gr_id = gr_id[i]
            board.bo_skin = bo_skin[i]
            board.bo_mobile_skin = bo_mobile_skin[i]
            board.bo_subject = bo_subject[i]
            board.bo_read_point = int(
                bo_read_point[i]) if bo_read_point[i] is not None and bo_read_point[i].isdigit() else 0
            board.bo_write_point = int(
                bo_write_point[i]) if bo_write_point[i] is not None and bo_write_point[i].isdigit() else 0
            board.bo_comment_point = int(
                bo_comment_point[i]) if bo_comment_point[i] is not None and bo_comment_point[i].isdigit() else 0
            board.bo_download_point = int(
                bo_download_point[i]) if bo_download_point[i] is not None and bo_download_point[i].isdigit() else 0
            board.bo_use_sns = get_from_list(bo_use_sns, i, 0)
            board.bo_use_search = get_from_list(bo_use_search, i, 0)
            board.bo_order = int(
                bo_order[i]) if bo_order[i] is not None and bo_order[i].isdigit() else 0
            board.bo_device = bo_device[i] if bo_device[i] is not None else ""
            db.commit()

            # 최신글 캐시 삭제
            G6FileCache().delete_prefix(f'latest-{board.bo_table}')

    return RedirectResponse(f"/admin/board_list?{request.query_params}", status_code=302)


@router.post("/board_list_delete", dependencies=[Depends(validate_token)])
async def board_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    bo_table: List[str] = Form(None, alias="bo_table[]"),
):
    """
    게시판관리 목록 일괄삭제
    """
    for i in checks:
        board = db.get(Board, bo_table[i])
        if board:
            # 게시판 관리 레코드 삭제
            db.delete(board)
            # 최신글 삭제
            db.execute(delete(BoardNew).where(BoardNew.bo_table == board.bo_table))
            # 스크랩 삭제
            db.execute(delete(Scrap).where(Scrap.bo_table == board.bo_table))
            # 파일 삭제
            db.execute(delete(BoardFile).where(BoardFile.bo_table == board.bo_table))
            # 좋아요 기록 삭제
            db.execute(delete(BoardGood).where(BoardGood.bo_table == board.bo_table))
            # 게시판 테이블 삭제
            Write = dynamic_create_write_table(table_name=board.bo_table, create_table=False)
            # FIXME: 게시판 생성 직후 삭제시 database locked 에러 발생
            Write.__table__.drop(engine)
            # 최신글 캐시 삭제
            G6FileCache().delete_prefix(f'latest-{board.bo_table}')

            db.commit()

    return RedirectResponse(f"/admin/board_list?{request.query_params}", status_code=303)


@router.get("/board_form")
async def board_form(request: Request, db: db_session):
    """
    게시판 등록 폼
    """
    config = request.state.config
    board = {
        "bo_table": "",
        "bo_count_delete": 1,
        "bo_count_modify": 1,
        "bo_read_point": config.cf_read_point,
        "bo_write_point": config.cf_write_point,
        "bo_comment_point": config.cf_comment_point,
        "bo_download_point": config.cf_download_point,
        "bo_gallery_cols": 4,
        "bo_gallery_width": 200,
        "bo_gallery_height": 150,
        "bo_mobile_gallery_width": 125,
        "bo_mobile_gallery_height": 100,
        "bo_table_width": 100,
        "bo_page_rows": config.cf_page_rows,
        "bo_mobile_page_rows": config.cf_mobile_page_rows,
        "bo_subject_len": 60,
        "bo_mobile_subject_len": 30,
        "bo_new": 24,
        "bo_hot": 100,
        "bo_image_width": 600,
        "bo_upload_count": 2,
        "bo_upload_size": 1048576,
        "bo_reply_order": 1,
        "bo_use_search": 1,
        "bo_skin": "basic",
        "bo_mobile_skin": "basic",
        "bo_use_secret": 0,
    }

    context = {
        "request": request,
        "board": board,
        "config": config,
    }
    return templates.TemplateResponse("board_form.html", context)


@router.get("/board_form/{bo_table}")
async def board_form(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
):
    """
    게시판 수정 폼
    """
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} 게시판이 존재하지 않습니다.", 404)

    context = {
        "request": request,
        "board": board,
        "config": request.state.config,
    }
    return templates.TemplateResponse("board_form.html", context)


@router.post("/board_form_update", dependencies=[Depends(validate_token)])
async def board_form_update(
    request: Request,
    db: db_session,
    sfl: str = Form(None),
    stx: str = Form(None),
    action: str = Form(...),
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
    """
    게시판 설정 등록, 수정 처리
    """
    # 등록
    if action == "w":
        existing_board = db.get(Board, bo_table)
        if existing_board:
            raise AlertException(f"{bo_table} 게시판아이디가 이미 존재합니다. (등록불가)", 400)

        # 게시판 설정 등록
        new_board = Board(bo_table=bo_table, **form_data.__dict__)
        db.add(new_board)
        db.commit()

        # 게시판 테이블 생성
        dynamic_create_write_table(table_name=bo_table, create_table=True)

    # 수정
    elif action == "u":
        existing_board = db.get(Board, bo_table)
        if not existing_board:
            raise AlertException(f"{bo_table} 게시판아이디가 존재하지 않습니다. (수정불가)", 404)

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_board, field, value)
        db.commit()

    else:
        raise AlertException("잘못된 접근입니다.", 400)

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
    if chk_all_device:
        chk_all['bo_device'] = form_data.bo_device
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
        boards = db.scalars(
            select(Board).where(Board.gr_id == form_data.gr_id)
        )
        for board in boards:
            for key, value in chk_grp.items():
                setattr(board, key, value)
            db.commit()

    # 전체적용 체크한 항목이 있다면
    if (chk_all):
        boards = db.scalars(select(Board)).all()
        for board in boards:
            for key, value in chk_all.items():
                setattr(board, key, value)
            db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return RedirectResponse(f"/admin/board_form/{bo_table}?{request.query_params}", status_code=303)


@router.get("/board_copy/{bo_table}")
async def board_copy(
    request: Request,
    db: db_session,
    bo_table: str = Path(...),
):
    """
    게시판 복사 폼
    """
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} 게시판이 존재하지 않습니다.", 404)

    context = {"request": request, "board": board}
    return templates.TemplateResponse("board_copy.html", context)


@router.post("/board_copy_update", dependencies=[Depends(validate_token)])
async def board_copy_update(
    request: Request,
    db: db_session,
    bo_table: str = Form(...),
    target_table: str = Form(...),
    target_subject: str = Form(...),
    copy_case: str = Form(...),
):
    """
    게시판 복사 처리
    """
    source_row = db.get(Board, bo_table)
    if not source_row:
        raise AlertException(f"{bo_table} 게시판이 존재하지 않습니다.", 404)

    target_row = db.get(Board, target_table)
    if target_row:
        raise AlertException(f"{bo_table} 게시판이 이미 존재합니다.", 404)

    # 복사될 레코드의 모든 필드를 딕셔너리로 변환
    target_dict = {key: value for key, value in source_row.__dict__.items() if not key.startswith('_')}
    
    target_dict['bo_table'] = target_table
    target_dict['bo_subject'] = target_subject

    target_row = Board(**target_dict)
    db.add(target_row)
    db.commit()

    # 새로운 게시판 테이블 생성
    source_write = dynamic_create_write_table(table_name=bo_table, create_table=False)
    target_write = dynamic_create_write_table(table_name=target_table, create_table=True)
    # 복사 유형을 '구조와 데이터' 선택시 테이블의 레코드 모두 복사
    if copy_case == 'schema_data_both':
        writes = db.scalars(select(source_write)).all()
        for write in writes:
            copy_data = {key: value for key, value in write.__dict__.items() if not key.startswith('_')}
            print(copy_data)
            # write 객체로 target_write 테이블에 레코드 추가
            db.execute(target_write.__table__.insert(), copy_data)
            db.commit()

    content = """
    <script>
        window.opener.location.href = "/admin/board_list";
        window.close();
    </script>
    """

    return HTMLResponse(content=content)
